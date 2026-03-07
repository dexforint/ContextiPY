from __future__ import annotations

from enum import Enum
from typing import Annotated

from pcontext.questions import (
    Ask,
    ImageQuery,
    Question,
    Questions,
    _build_question_form_schema,
)
from pcontext.runtime.ipc_models import AgentEndpoint
from pcontext.runtime.question_models import AskUserResponse


class Gender(str, Enum):
    male = "Male"
    female = "Female"


class DemoQuestions(Questions):
    name: Annotated[str, "Имя"]
    age: Annotated[int, Question(title="Возраст", ge=18, le=99)] = 21
    gender: Annotated[Gender, "Пол"] = Gender.male
    photo: Annotated[str, Question(title="Фото", format=ImageQuery)] = ""


def test_build_question_form_schema_extracts_fields() -> None:
    """
    Схема Ask-формы должна корректно извлекаться из Questions-класса.
    """
    schema = _build_question_form_schema(DemoQuestions)

    assert schema.model_name == "DemoQuestions"
    assert len(schema.fields) == 4

    assert schema.fields[0].name == "name"
    assert schema.fields[0].required is True
    assert schema.fields[0].title == "Имя"

    assert schema.fields[1].name == "age"
    assert schema.fields[1].required is False
    assert schema.fields[1].ge == 18
    assert schema.fields[1].le == 99

    assert schema.fields[2].value_kind == "enum"
    assert schema.fields[2].enum_values == ["Male", "Female"]

    assert schema.fields[3].format == "image_path"


def test_ask_returns_typed_answers(monkeypatch) -> None:
    """
    Ask(...) должен возвращать экземпляр Questions-класса
    с уже приведёнными типами.
    """
    monkeypatch.setattr(
        "pcontext.questions.read_agent_endpoint",
        lambda _path: AgentEndpoint(
            host="127.0.0.1",
            port=1,
            token="token",
            pid=123,
        ),
    )
    monkeypatch.setattr(
        "pcontext.questions.send_request",
        lambda _endpoint, _request, timeout_seconds=3600.0: AskUserResponse(
            cancelled=False,
            answers={
                "name": "Alex",
                "age": 30,
                "gender": "Female",
                "photo": "C:/tmp/image.png",
            },
        ),
    )

    answers = Ask(DemoQuestions)

    assert answers is not None
    assert isinstance(answers, DemoQuestions)
    assert answers.name == "Alex"
    assert answers.age == 30
    assert answers.gender is Gender.female
    assert answers.photo == "C:/tmp/image.png"


def test_ask_returns_none_when_cancelled(monkeypatch) -> None:
    """
    Если пользователь закрыл Ask-диалог, Ask(...) должен вернуть None.
    """
    monkeypatch.setattr(
        "pcontext.questions.read_agent_endpoint",
        lambda _path: AgentEndpoint(
            host="127.0.0.1",
            port=1,
            token="token",
            pid=123,
        ),
    )
    monkeypatch.setattr(
        "pcontext.questions.send_request",
        lambda _endpoint, _request, timeout_seconds=3600.0: AskUserResponse(
            cancelled=True,
            answers={},
        ),
    )

    result = Ask(DemoQuestions)
    assert result is None
