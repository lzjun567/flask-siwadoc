__all__ = ['ValidationError']

from pydantic import ValidationError as PydanticError


class ValidationError(PydanticError):
    def __init__(self, e: PydanticError):
        super(ValidationError, self).__init__(errors=e.raw_errors, model=e.model, )

    pass
