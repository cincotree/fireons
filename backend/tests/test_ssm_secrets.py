from ssm_secrets import load_ssm_parameters


class FakeSsmClient:
    def __init__(self, pages: list[dict]):
        self.pages = pages
        self.requests: list[dict] = []

    def get_parameters_by_path(self, **request):
        self.requests.append(request)
        return self.pages[len(self.requests) - 1]


def _param(name: str, value: str) -> dict:
    return {"Name": name, "Value": value}


def test_no_prefix_is_a_no_op():
    environ: dict[str, str] = {}

    class ExplodingClient:
        def get_parameters_by_path(self, **request):
            raise AssertionError("SSM must not be called without SSM_PREFIX")

    assert load_ssm_parameters(client=ExplodingClient(), environ=environ) == []
    assert environ == {}


def test_loads_parameters_into_environment_by_last_path_segment():
    environ = {"SSM_PREFIX": "/fireons/prod/"}
    client = FakeSsmClient(
        [
            {
                "Parameters": [
                    _param("/fireons/prod/SECRET_KEY", "jwt-secret"),
                    _param("/fireons/prod/DATABASE_URL", "postgresql://u:p@h/db"),
                ]
            }
        ]
    )

    loaded = load_ssm_parameters(client=client, environ=environ)

    assert loaded == ["SECRET_KEY", "DATABASE_URL"]
    assert environ["SECRET_KEY"] == "jwt-secret"
    assert environ["DATABASE_URL"] == "postgresql://u:p@h/db"
    assert client.requests == [{"Path": "/fireons/prod", "Recursive": False, "WithDecryption": True}]


def test_follows_pagination():
    environ: dict[str, str] = {}
    client = FakeSsmClient(
        [
            {"Parameters": [_param("/fireons/prod/SECRET_KEY", "a")], "NextToken": "page-2"},
            {"Parameters": [_param("/fireons/prod/ORIGIN_VERIFY_SECRET", "b")]},
        ]
    )

    loaded = load_ssm_parameters(prefix="fireons/prod", client=client, environ=environ)

    assert loaded == ["SECRET_KEY", "ORIGIN_VERIFY_SECRET"]
    assert client.requests[1]["NextToken"] == "page-2"
    assert environ == {"SECRET_KEY": "a", "ORIGIN_VERIFY_SECRET": "b"}


def test_existing_environment_variables_take_precedence():
    environ = {"SECRET_KEY": "from-lambda-env"}
    client = FakeSsmClient([{"Parameters": [_param("/fireons/prod/SECRET_KEY", "from-ssm")]}])

    loaded = load_ssm_parameters(prefix="/fireons/prod", client=client, environ=environ)

    assert loaded == []
    assert environ["SECRET_KEY"] == "from-lambda-env"
