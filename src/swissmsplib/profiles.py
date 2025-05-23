import logging
import os
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)


class ProviderProfile:
    def __init__(
        self,
        provider: str,
        username: str,
        password: str,
        refresh_token: str | None = None,
    ):
        self.provider = provider
        self.username = username
        self.password = password
        self.refresh_token = refresh_token


def read_profile(profile_name):
    """
    Reads a provider profile from the default profile file.
    On Linux: $HOME/.config/swissmsplib/profiles.toml
    """
    profile_file_path = __get_config_path()

    profile = __read_toml_config(profile_file_path, profile_name)

    if not profile:
        raise Exception("profile is not defined")

    # Final check after reading all sources
    if not profile.username:
        raise Exception("username is not defined")
    if not profile.password:
        raise Exception("password is not defined")

    return profile


def __get_config_path():
    profile_file = os.environ.get("PROFILE_FILE", None)
    if not profile_file:
        profile_file = Path.home().joinpath(f".config/swissmsplib/profiles.toml")

    return profile_file


def __read_toml_config(profile_file_path, profile_name) -> ProviderProfile | None:
    with open(profile_file_path, mode="rb") as fp:
        profiles = tomllib.load(fp)
        if not profile_name in profiles:
            return None

        profile_entry = profiles[profile_name]
        return ProviderProfile(
            profile_entry["provider"],
            profile_entry["username"],
            profile_entry["password"],
            profile_entry.get("refresh_token", None),
        )
