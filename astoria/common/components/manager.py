"""State Manager base class."""
import asyncio
import logging
import signal
import sys
from abc import ABCMeta, abstractmethod
from json import JSONDecodeError, loads
from signal import SIGHUP, SIGINT, SIGTERM
from types import FrameType
from typing import (
    Callable,
    Coroutine,
    Generic,
    List,
    Match,
    Optional,
    Type,
    TypeVar,
)

from pydantic import ValidationError, parse_obj_as

from astoria import __version__
from astoria.common.config import AstoriaConfig
from astoria.common.ipc import ManagerMessage, ManagerRequest, RequestResponse
from astoria.common.mqtt.wrapper import MQTTWrapper

LOGGER = logging.getLogger(__name__)

loop = asyncio.get_event_loop()

T = TypeVar("T", bound=ManagerMessage)
RequestT = TypeVar("RequestT", bound=ManagerRequest)


class StateManager(Generic[T], metaclass=ABCMeta):
    """
    State Manager.

    A process that stores and mutates some state.
    """

    config: AstoriaConfig
    _status: T

    def __init__(self, verbose: bool, config_file: Optional[str]) -> None:
        self.config = AstoriaConfig.load(config_file)

        self._setup_logging(verbose)
        self._setup_event_loop()
        self._setup_mqtt()

        self._init()

    def _setup_logging(self, verbose: bool, *, welcome_message: bool = True) -> None:
        if verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format=f"%(asctime)s {self.name} %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format=f"%(asctime)s {self.name} %(levelname)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # Suppress INFO messages from gmqtt
            logging.getLogger("gmqtt").setLevel(logging.WARNING)

        if welcome_message:
            LOGGER.info(f"{self.name} v{__version__} - {self.__doc__}")

    def _setup_event_loop(self) -> None:
        self._stop_event = asyncio.Event()

        loop.add_signal_handler(SIGHUP, self.halt)
        loop.add_signal_handler(SIGINT, self.halt)
        loop.add_signal_handler(SIGTERM, self.halt)

    def _setup_mqtt(self) -> None:
        self._mqtt = MQTTWrapper(
            self.name,
            self.config.mqtt,
            last_will=self.offline_status,
            dependencies=self.dependencies,
            no_dependency_event=self._stop_event,
        )

    def _init(self) -> None:
        """
        Initialisation of the data component.

        Called in the constructor of the parent class.
        """
        pass

    def _exit(self, signals: signal.Signals, frame_type: FrameType) -> None:
        sys.exit(0)

    @property
    @abstractmethod
    def name(self) -> str:
        """
        MQTT client name of the data component.

        This should be unique, as clashes will cause unexpected disconnections.
        """
        raise NotImplementedError

    @property
    def dependencies(self) -> List[str]:
        """State Managers to depend on."""
        return []

    @property
    def status(self) -> T:
        """Get the status of the state manager."""
        return self._status

    @status.setter
    def status(self, status: T) -> None:
        """Set the status of the state manager."""
        self._status = status
        self._mqtt.publish("", status, retain=True)

    @property
    @abstractmethod
    def offline_status(self) -> T:
        """
        Status to publish when the manager goes offline.

        This status should ensure that any other components relying
        on this data go into a safe state.
        """
        raise NotImplementedError

    async def run(self) -> None:
        """Entrypoint for the data component."""
        await self._mqtt.connect()
        LOGGER.info("Connected to MQTT broker.")
        await self._mqtt.wait_dependencies()

        await self.main()
        self.status = self.offline_status
        await self._mqtt.disconnect()

    async def wait_loop(self) -> None:
        """Wait until the data component is halted."""
        await self._stop_event.wait()

    def halt(self, *, silent: bool = False) -> None:
        """Stop the component."""
        if not silent:
            LOGGER.info("Halting")
        self._stop_event.set()

    @abstractmethod
    async def main(self) -> None:
        """Main method of the data component."""
        raise NotImplementedError

    def _register_request(
        self,
        name: str,
        typ: Type[RequestT],
        handler: Callable[[RequestT], Coroutine[None, None, RequestResponse]],
    ) -> None:
        LOGGER.debug(f"Registering {name} request for {self.name} component")

        async def _handler(match: Match[str], payload: str) -> None:
            try:
                req = parse_obj_as(typ, loads(payload))
                response = await handler(req)
                self._mqtt.publish(
                    f"request/{name}/{req.uuid}",
                    response,
                )
            except JSONDecodeError:
                LOGGER.warning(
                    f"Received {name} request, but unable to decode JSON: {payload}",
                )
            except ValidationError as e:
                LOGGER.warning(
                    f"Received {name} request, but it was not valid: {payload}",
                )
                LOGGER.warning(str(e))

        self._mqtt.subscribe(f"{self.name}/request/{name}", _handler)
