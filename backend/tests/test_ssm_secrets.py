from ssm_secrets import load_ssm_parameters


class FakeSsmClient:
    def __init__(self, pages: list[dict]):
        self.pages = pages
        self.requests: list[dict] = []

    def get_parameters_by_path(self, **request):
        self.requests.append(request)
        return self.pages[len(self.requests) - 1]


def test_loads_all_pages_without_overriding_existing_env():
    environ = {"SSM_PREFIX": "/fireons/prod", "SECRET_KEY": "from-env"}
    client = FakeSsmClient(
        [
            {
                "Parameters": [
                    {"Name": "/fireons/prod/SECRET_KEY", "Value": "from-ssm"},
                    {"Name": "/fireons/prod/DATABASE_URL", "Value": "postgresql://h/db"},
                ],
                "NextToken": "page-2",
            },
            {"Parameters": [{"Name": "/fireons/prod/ORIGIN_VERIFY_SECRET", "Value": "s"}]},
        ]
    )

    assert load_ssm_parameters(client=client, environ=environ) == ["DATABASE_URL", "ORIGIN_VERIFY_SECRET"]
    assert environ["SECRET_KEY"] == "from-env"
    assert client.requests[1]["NextToken"] == "page-2"


def test_no_prefix_is_a_no_op():
    assert load_ssm_parameters(client=None, environ={}) == []
