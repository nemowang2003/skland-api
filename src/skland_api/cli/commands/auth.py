import typing
from collections.abc import Callable

import rich_click as click
import tomlkit
from tomlkit.items import Table

from skland_api.cli.core import (
    AuthFailure,
    GlobalOption,
    get_auth_file,
    load_auth_info,
    remove_auth_info,
    save_auth_info,
    skland_command,
    skland_group,
)
from skland_api.models import AuthInfo


def get_input(
    text: str, validator: Callable[[str], str | None] | None = None, hide_input: bool = False
) -> str | None:
    while True:
        val = click.prompt(text, default="", hide_input=hide_input, show_default=False)
        if val == "":
            return None
        if validator is None:
            return val
        msg = validator(val)
        if msg is None:
            return val
        click.echo(msg)


@skland_command(name="add")
@click.argument("username", required=False)
@click.option("--phone")
@click.option("--password")
@click.option("--token")
@click.option("--cred")
@click.option(
    "--interactive/--no-interactive",
    is_flag=True,
    default=True,
    help="[允许/禁止]交互式询问认证信息",
)
@click.option("--force", is_flag=True, default=False, help="允许强制覆盖原有的认证信息")
async def auth_add(
    global_option: GlobalOption,
    username: str | None,
    phone: str | None,
    password: str | None,
    token: str | None,
    cred: str | None,
    interactive: bool,
    force: bool,
):
    if username is None:
        if not interactive:
            ctx = typing.cast(click.Context, click.get_current_context())
            ctx.fail("在非交互模式 (--no-interactive) 下，必须提供 USERNAME 参数")
        username = click.prompt("skland-api 用户标识符")

    global_option.config_content.setdefault(username, tomlkit.table())
    if not isinstance(global_option.config_content.item(username), Table):
        global_option.config_content[username] = tomlkit.table()

    if not force and get_auth_file(global_option.auth_dir, username).exists():
        raise click.ClickException("该用户已存在，使用 --force 以强制覆盖")

    if interactive:
        if phone is None:
            phone = get_input("手机号", validator=AuthInfo.check_phone)
        if password is None and phone is not None:
            password = get_input("密码", hide_input=True)
        if token is None:
            token = get_input("Token (24 位)", validator=AuthInfo.check_token)
        if cred is None:
            cred = get_input("Cred (32 位)", validator=AuthInfo.check_cred)

    try:
        auth_info = AuthInfo(
            phone=phone,
            password=password,
            token=token,
            cred=cred,
        )
        await auth_info.full_auth()
    except ValueError as e:
        raise click.ClickException(str(e))

    save_auth_info(global_option.auth_dir, username, auth_info)
    global_option.writeback()


@skland_command(name="remove")
@click.argument("username", required=False)
def auth_remove(global_option: GlobalOption, username: str | None):
    usernames = [k for k in global_option.config_content.keys()]
    if not usernames:
        click.echo("未配置任何账号")
        return

    if username is None:
        username = click.prompt(
            "请输入要删除的用户名",
            type=click.Choice(usernames),
        )

    removed = remove_auth_info(global_option.auth_dir, username)
    table = global_option.config_content.get(username)
    if isinstance(table, Table) and len(table) == 0:
        del global_option.config_content[username]
    elif table is not None and not isinstance(table, Table):
        del global_option.config_content[username]

    if not removed and username not in global_option.config_content:
        raise click.ClickException(f"用户 {username!r} 不存在")

    click.echo(f"已删除用户 {username!r} 的认证信息")
    global_option.writeback()


@skland_command(name="list")
def auth_list(global_option: GlobalOption):
    usernames = [k for k in global_option.config_content.keys()]
    if not usernames:
        click.echo("未配置任何账号")
        return

    for username in usernames:
        auth_file = get_auth_file(global_option.auth_dir, username)
        if not auth_file.exists():
            continue

        try:
            auth_info = load_auth_info(global_option.auth_dir, username)
        except AuthFailure as e:
            click.echo(f"{username!r} 账号配置异常: {e.format_message()}")
            continue
        phone = auth_info.phone or "<未设置>"
        token = "<已设置>" if auth_info.token else "<未设置>"
        cred = "<已设置>" if auth_info.cred else "<未设置>"
        click.echo(f"{username!r}: 手机号={phone}, token={token}, cred={cred}")


@skland_group(name="auth", help="账号信息管理")
def auth(ctx: click.Context):
    pass


auth.add_command(auth_add)
auth.add_command(auth_remove)
auth.add_command(auth_list)
