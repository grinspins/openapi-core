from json import dumps

from falcon import API
from falcon.testing import TestClient
import pytest

from openapi_core.contrib.falcon.middlewares import FalconOpenAPIMiddleware
from openapi_core.shortcuts import create_spec
from openapi_core.validation.request.datatypes import RequestParameters


class TestFalconOpenAPIMiddleware(object):

    view_response_callable = None

    @pytest.fixture
    def spec(self, factory):
        specfile = 'contrib/falcon/data/v3.0/falcon_factory.yaml'
        return create_spec(factory.spec_from_file(specfile))

    @pytest.fixture
    def middleware(self, spec):
        return FalconOpenAPIMiddleware.from_spec(spec)

    @pytest.fixture
    def app(self, middleware):
        return API(middleware=[middleware])

    @pytest.yield_fixture
    def client(self, app):
        return TestClient(app)

    @pytest.fixture
    def view_response(self):
        def view_response(*args, **kwargs):
            return self.view_response_callable(*args, **kwargs)
        return view_response

    @pytest.fixture(autouse=True)
    def details_view(self, app, view_response):
        class BrowseDetailResource(object):
            def on_get(self, *args, **kwargs):
                return view_response(*args, **kwargs)

        resource = BrowseDetailResource()
        app.add_route("/browse/{id}", resource)
        return resource

    @pytest.fixture(autouse=True)
    def list_view(self, app, view_response):
        class BrowseListResource(object):
            def on_get(self, *args, **kwargs):
                return view_response(*args, **kwargs)

        resource = BrowseListResource()
        app.add_route("/browse", resource)
        return resource

    def test_invalid_content_type(self, client):
        def view_response_callable(request, response, id):
            from falcon.constants import MEDIA_HTML
            from falcon.status_codes import HTTP_200
            assert request.openapi
            assert not request.openapi.errors
            assert request.openapi.parameters == RequestParameters(path={
                'id': 12,
            })
            response.content_type = MEDIA_HTML
            response.status = HTTP_200
            response.body = 'success'
        self.view_response_callable = view_response_callable
        headers = {'Content-Type': 'application/json'}
        result = client.simulate_get(
            '/browse/12', host='localhost', headers=headers)

        assert result.json == {
            'errors': [
                {
                    'class': (
                        "<class 'openapi_core.schema.media_types.exceptions."
                        "InvalidContentType'>"
                    ),
                    'status': 415,
                    'title': (
                        'Content for following mimetype not found: text/html'
                    )
                }
            ]
        }

    def test_server_error(self, client):
        headers = {'Content-Type': 'application/json'}
        result = client.simulate_get(
            '/browse/12', host='localhost', headers=headers, protocol='https')

        expected_data = {
            'errors': [
                {
                    'class': (
                        "<class 'openapi_core.templating.paths.exceptions."
                        "ServerNotFound'>"
                    ),
                    'status': 400,
                    'title': (
                        'Server not found for '
                        'https://localhost/browse/12'
                    ),
                }
            ]
        }
        assert result.status_code == 400
        assert result.json == expected_data

    def test_operation_error(self, client):
        headers = {'Content-Type': 'application/json'}
        result = client.simulate_post(
            '/browse/12', host='localhost', headers=headers)

        expected_data = {
            'errors': [
                {
                    'class': (
                        "<class 'openapi_core.templating.paths.exceptions."
                        "OperationNotFound'>"
                    ),
                    'status': 405,
                    'title': (
                        'Operation post not found for '
                        'http://localhost/browse/12'
                    ),
                }
            ]
        }
        assert result.status_code == 405
        assert result.json == expected_data

    def test_path_error(self, client):
        headers = {'Content-Type': 'application/json'}
        result = client.simulate_get(
            '/browse', host='localhost', headers=headers)

        expected_data = {
            'errors': [
                {
                    'class': (
                        "<class 'openapi_core.templating.paths.exceptions."
                        "PathNotFound'>"
                    ),
                    'status': 404,
                    'title': (
                        'Path not found for '
                        'http://localhost/browse'
                    ),
                }
            ]
        }
        assert result.status_code == 404
        assert result.json == expected_data

    def test_endpoint_error(self, client):
        headers = {'Content-Type': 'application/json'}
        result = client.simulate_get(
            '/browse/invalidparameter', host='localhost', headers=headers)

        expected_data = {
            'errors': [
                {
                    'class': (
                        "<class 'openapi_core.unmarshalling.schemas.exceptions"
                        ".InvalidSchemaValue'>"
                    ),
                    'status': 400,
                    'title': (
                        "Value invalidparameter not valid for schema of type "
                        "SchemaType.INTEGER: Failed to cast value "
                        "invalidparameter to type integer"
                    )
                }
            ]
        }
        assert result.status_code == 400
        assert result.json == expected_data

    def test_valid(self, client):
        def view_response_callable(request, response, id):
            from falcon.constants import MEDIA_JSON
            from falcon.status_codes import HTTP_200
            assert request.openapi
            assert not request.openapi.errors
            assert request.openapi.parameters == RequestParameters(path={
                'id': 12,
            })
            response.status = HTTP_200
            response.content_type = MEDIA_JSON
            response.body = dumps({
                'data': 'data',
            })
        self.view_response_callable = view_response_callable

        headers = {'Content-Type': 'application/json'}
        result = client.simulate_get(
            '/browse/12', host='localhost', headers=headers)

        assert result.status_code == 200
        assert result.json == {
            'data': 'data',
        }
