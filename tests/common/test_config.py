from __future__ import annotations

# Standard Library Imports
from argparse import ArgumentParser
from os import environ
from typing import Annotated, Optional

# Third Party Imports
import pytest
from pydantic import BaseModel, Field

# RESONAATE Imports
from resonaate.common.config import RootConfig, getConfig, putResonaateArgs, userSpecFactory
from resonaate.common.config.meta import (
    CommandLineOptions,
    EnvName,
    UserFieldCollection,
    UserFieldInfo,
)

# ruff: noqa: UP045, UP007


def test_getConfig():
    """Initial test of 'end-to-end' config pipeline."""
    putResonaateArgs(["configs/json/main_init.json"])
    cfg = getConfig()
    assert isinstance(cfg, RootConfig)


field_label: str = "root_field"


class NoCustomMetadata(BaseModel):
    """Test pydantic model to make sure custom :class:`.UserSpec` stuff works."""

    root_field: Annotated[
        Optional[str],
        Field(default=field_label, description="a root field with no custom metadata"),
    ]


def test_userSpecFactory_noCustomMetadata():
    """Test :meth:`.userSpecFactory()` on a field that doesn't have any custom metadata."""
    user_spec = userSpecFactory(NoCustomMetadata.__name__, NoCustomMetadata)
    assert isinstance(user_spec, UserFieldCollection)
    with pytest.raises(AttributeError):
        _ = user_spec.getSpec("foo")

    field_spec = user_spec.getSpec(field_label)
    assert isinstance(field_spec, UserFieldInfo)
    assert field_spec.env_name is None
    assert field_spec.cli_options is None

    parser = ArgumentParser()
    field_spec.addToArgParser(parser)
    help_str = parser.format_help()
    assert field_label not in help_str

    # make sure no input works as expected
    test_user_in = {}
    field_spec.retrieveUserInput(test_user_in, {}, {})
    assert not test_user_in


class HasCliOption(BaseModel):
    """Test pydantic model to make sure custom :class:`.UserSpec` stuff works."""

    root_field: Annotated[
        Optional[str],
        Field(default=field_label, description="a root field accessible via cli"),
        CommandLineOptions("-r", "--root-field"),
    ]


def test_userSpecFactory_hasCliOption():
    """Test :meth:`.userSpecFactory()` on a field that is accessible via the CLI."""
    user_spec = userSpecFactory(HasCliOption.__name__, HasCliOption)
    assert isinstance(user_spec, UserFieldCollection)

    field_spec = user_spec.getSpec(field_label)
    assert isinstance(field_spec, UserFieldInfo)
    assert field_spec.env_name is None
    assert field_spec.cli_options is not None

    parser = ArgumentParser()
    field_spec.addToArgParser(parser)
    help_str = parser.format_help()
    assert field_label in help_str

    # make sure no input works as expected
    test_user_in = {}
    field_spec.retrieveUserInput(test_user_in, {}, {})
    assert not test_user_in

    # if cli is provided, it should be retrieved as input
    user_input = "user root field"
    field_spec.retrieveUserInput(test_user_in, {field_label: user_input}, {})
    assert test_user_in[field_label] == user_input


class HasEnvName(BaseModel):
    """Test pydantic model to make sure custom :class:`.UserSpec` stuff works."""

    root_field: Annotated[
        Optional[str],
        Field(default=field_label, description="a root field accessible via env"),
        EnvName("ROOT_FIELD"),
    ]


def test_userSpecFactory_hasEnvName(monkeypatch):
    """Test :meth:`.userSpecFactory()` on a field that is accessible via env.

    Args:
        monkeypatch: Pytest builtin fixture for patching functionality.
    """
    user_spec = userSpecFactory(HasEnvName.__name__, HasEnvName)
    assert isinstance(user_spec, UserFieldCollection)

    field_spec = user_spec.getSpec(field_label)
    assert isinstance(field_spec, UserFieldInfo)
    assert field_spec.env_name is not None
    assert field_spec.cli_options is None

    parser = ArgumentParser()
    field_spec.addToArgParser(parser)
    help_str = parser.format_help()
    assert field_label not in help_str

    # make sure no input works as expected
    test_user_in = {}
    field_spec.retrieveUserInput(test_user_in, {}, {})
    assert not test_user_in

    # if environment variable is populated, it should be retrieved as input
    user_input = "user root field"
    monkeypatch.setitem(environ, field_spec.env_name.name, user_input)
    field_spec.retrieveUserInput(test_user_in, {}, {})
    assert test_user_in[field_label] == user_input

    # if environment variable and dotenv is populated, the dotenv input should take precedence
    test_user_in = {}
    override = "override!"
    field_spec.retrieveUserInput(test_user_in, {}, {field_spec.env_name.name: override})
    assert test_user_in[field_label] == override


class HasBoth(BaseModel):
    """Test pydantic model to make sure custom :class:`.UserSpec` stuff works."""

    root_field: Annotated[
        Optional[str],
        Field(default=field_label, description="a root field accessible via cli and env"),
        CommandLineOptions("-r", "--root-field"),
        EnvName("ROOT_FIELD"),
    ]


def test_userSpecFactory_hasBoth(monkeypatch):
    """Test :meth:`.userSpecFactory()` on a field that is accessible via cli and env.

    Args:
        monkeypatch: Pytest builtin fixture for patching functionality.
    """
    user_spec = userSpecFactory(HasBoth.__name__, HasBoth)
    assert isinstance(user_spec, UserFieldCollection)

    field_spec = user_spec.getSpec(field_label)
    assert isinstance(field_spec, UserFieldInfo)
    assert field_spec.env_name is not None
    assert field_spec.cli_options is not None

    parser = ArgumentParser()
    field_spec.addToArgParser(parser)
    help_str = parser.format_help()
    assert field_label in help_str

    # make sure no input works as expected
    test_user_in = {}
    field_spec.retrieveUserInput(test_user_in, {}, {})
    assert not test_user_in

    # if cli input is provided, it should be retrieved as input
    test_user_in = {}
    cli_input = "input from cli"
    field_spec.retrieveUserInput(test_user_in, {field_label: cli_input}, {})
    assert test_user_in[field_label] == cli_input

    # if environment variable is populated, it should be retrieved as input
    test_user_in = {}
    env_input = "input from env"
    monkeypatch.setitem(environ, field_spec.env_name.name, env_input)
    field_spec.retrieveUserInput(test_user_in, {}, {})
    assert test_user_in[field_label] == env_input

    # if environment variable and dotenv is populated, the dotenv input should take precedence
    test_user_in = {}
    dotenv_input = "input from dotenv"
    field_spec.retrieveUserInput(test_user_in, {}, {field_spec.env_name.name: dotenv_input})
    assert test_user_in[field_label] == dotenv_input

    # if all user input is populated, the cli input should take precedence
    test_user_in = {}
    field_spec.retrieveUserInput(
        test_user_in,
        {field_label: cli_input},
        {field_spec.env_name.name: dotenv_input},
    )
    assert test_user_in[field_label] == cli_input
