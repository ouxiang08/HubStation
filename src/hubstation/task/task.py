"""Example"""
import asyncio
from typing import Callable, Any, Type, Tuple, Dict, Optional
from functools import partial


class BaseTask:
    """base task"""

    def run(self) -> bool:
        """Run task"""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop task"""
        raise NotImplementedError


class FileTask(BaseTask):
    """File task"""

    def run(self) -> bool:
        pass

    def stop(self) -> None:
        pass


class NetworkTask(BaseTask):
    """Network task"""

    def run(self) -> bool:
        pass

    def stop(self) -> None:
        pass


KwargsType = Dict[str, Any]
ArgsType = Tuple[Any]


async def run_in_executor(
        func: Callable[..., Any],
        args: Optional[ArgsType] = (),
        kwargs: Optional[KwargsType] = None
) -> Any:
    """Wrap a func in a threading executor """
    if kwargs:
        func = partial(func, **kwargs)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)


def task_runner(task_kls: Type[BaseTask]) -> None:
    """task runner"""
    task = task_kls()
    asyncio.run(run_in_executor(task.run))
