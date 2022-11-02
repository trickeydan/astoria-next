"""Test Manager Application."""

import asyncio
import logging
from typing import Optional

import click
from pydantic import BaseModel

from astoria.common.service import Service

LOGGER = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


@click.command("asttestd")
@click.option("-v", "--verbose", is_flag=True)
@click.option("-c", "--config-file", type=click.Path(exists=True))
def main(*, verbose: bool, config_file: Optional[str]) -> None:
    """Test Manager Application Entrypoint."""
    testd = TestManager(verbose, config_file)
    loop.run_until_complete(testd.run())


class TestState(BaseModel):
    """Test state."""

    data: str = "bees"


class TestManager(Service[TestState]):
    """Astoria Test State Manager."""

    name = "asttestd"
    dependencies = ["astdiskd"]

    def _init(self) -> None:
        pass

    @property
    def offline_state(self) -> TestState:
        """
        Status to publish when the manager goes offline.

        This status should ensure that any other components relying
        on this data go into a safe state.
        """
        return TestState()

    async def main(self) -> None:
        """Main routine for asttestd."""
        self.state = TestState(data="extra")

        # Wait whilst the program is running.
        await self.wait_loop()


if __name__ == "__main__":
    main()
