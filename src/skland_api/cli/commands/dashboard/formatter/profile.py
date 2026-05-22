from rich.rule import Rule
from rich.text import Text

from skland_api.modules.profile import Profile
from skland_api.modules.profile import main as module_entry

from . import render


@render.register
def render_profile(profile: Profile) -> Rule:
    text = Text()

    text.append(profile.nickname, style="green bold")
    text.append("#")
    text.append(profile.suffix, style="green bold")

    return Rule(text)


__all__ = ["module_entry"]
