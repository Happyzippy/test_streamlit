import json
import logging
import os
import requests
from urllib.parse import urlparse, unquote
from pydantic import BaseModel, PrivateAttr, parse_raw_as
from typing import List, Union, Type

from brevettiai.io.utils import IoTools, prompt_for_password
from brevettiai.platform.datamodel import backend, PlatformBackend
from brevettiai.platform.platform_credentials import PlatformDatasetCredentials
from brevettiai.platform.datamodel import web_api_types as api
from brevettiai.platform.datamodel import Dataset, Tag


log = logging.getLogger(__name__)


class PlatformAPI:
    """
    API interface to brevetti platform

    use `BREVETTI_AI_USER` and `BREVETTI_AI_PW` environment variables to use
    system-wide default username and password
    """
    def __init__(self, username=None, password=None, host=None,
                 remember_me: bool = False, cache_remote_files: bool = True):
        self.host = host or backend
        self.session = requests.session()

        username = username
        password = password

        self.user = self.login(username, password, remember_me=remember_me)
        self._io = IoTools().factory()
        self.io.minio.credentials = PlatformDatasetCredentials(self)

        if cache_remote_files:
            pass
            #self.io.set_cache_root(os.getenv(env_variables.BREVETTI_AI_CACHE, None))

    @property
    def host(self):
        return self._host.host if isinstance(self._host, PlatformBackend) else self._host

    @host.setter
    def host(self, host):
        self._host = host

    @property
    def io(self):
        return self._io

    @property
    def backend(self):
        if isinstance(self._host, PlatformBackend):
            return self._host
        else:
            raise AttributeError("Backend unknown")

    def login(self, username, password, remember_me=False):
        if username is None:
            username = input(f"{self.host} - username: ")
        if password is None:
            password = prompt_for_password()

        res = self.session.post(self.host + "/api/account/token", data=dict(userName=username, password=password))
        if not res.ok:
            raise PermissionError(f"Could not log in: {res.reason}")

        data = res.json()
        return data

    def _http_get(self, url, headers=None, **kwargs):
        if headers is None and url.startswith(self.host):
            headers = self.antiforgery_headers

        r = self.session.get(url, headers=headers, **kwargs)
        if not r.ok:
            if r.status_code == 401:
                raise PermissionError("Not authorized")
            raise requests.HTTPError(r.reason)
        return r

    def _http_post(self, url, headers=None, **kwargs):
        if headers is None and url.startswith(self.host):
            headers = self.antiforgery_headers

        r = self.session.post(url, headers=headers, **kwargs)
        if not r.ok:
            if r.status_code == 401:
                raise PermissionError("Not authorized")
            raise requests.HTTPError(r.reason)
        return r

    def _http_delete(self, url, headers=None, **kwargs):
        if headers is None and url.startswith(self.host):
            headers = self.antiforgery_headers

        r = self.session.delete(url, headers=headers, **kwargs)
        if not r.ok:
            if r.status_code == 401:
                raise PermissionError("Not authorized")
            raise requests.HTTPError(r.reason)
        return r

    @property
    def antiforgery_headers(self):
        """Get anti forgery headers from platform"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.user['token']
        }
        r = self.session.get(self.host + "/api/account/antiforgery", headers=headers)
        return {**headers, 'X-XSRF-TOKEN': r.json()['requestToken']}

    def get_dataset(self, id: str = None, write_access=False, **kwargs) -> Union[Dataset, List[Dataset]]:
        """
        Get dataset, or list of all datasets

        Args:
            id: dataset id
            write_access: resolve accessrights to the dataset
            **kwargs: Extended search criteria: use ('name', 'reference' 'locked', ...)

        Returns:
            dataset if id is given, otherwise list of datasets
        """
        url = self.host + "/api/data"
        url = url if id is None else url + "/" + id
        r = self._http_get(url)

        if id is None:
            return [Dataset(**x, backend=self.backend, io=self._io, resolve_access_rights=write_access)
                    for x in r.json() if all(x.get(k) == v for k, v in kwargs.items())]
        else:
            return Dataset(**r.json(), backend=self.backend, io=self._io, resolve_access_rights=write_access)

    def get_tag(self, id=None) -> Union[Tag, List[Tag]]:
        """
        Get tag or list of all tags

        Args:
            id: Tag id

        Returns:
            tag if id is given, otherwise a list of tags
        """
        url = self.host + "/api/resources/tags"
        url = url if id is None else url + "/" + id
        r = self._http_get(url)
        return parse_raw_as(Union[Tag, List[Tag]], r.content)

    def get_model(self, id=None, **kwargs) -> Union[api.Model, List[api.Model]]:
        """
        Get model or list of all models

        Args:
            id: model id
            **kwargs: Extended search criteria: use ('name', 'reference' 'locked', ...)

        Returns:
            model if id is given, otherwise a list of models
        """
        url = self.host + "/api/models"
        url = url if id is None else url + "/" + id
        r = self._http_get(url)
        if id is None:
            models = parse_raw_as(List[api.Model], r.content)
            return [x for x in models if all(getattr(x, k, None) == v for k, v in kwargs.items())]
        else:
            return parse_raw_as(api.Model, r.content)

    def get_report(self, id=None, **kwargs) -> Union[api.Report, List[api.Report]]:
        """
        Get test report, or list of all reports

        Args:
            id: report id
            **kwargs: Extended search criteria: use ('name', 'reference' 'locked', ...)

        Returns:
            report if id is given, otherwise a list of reports
        """
        url = self.host + "/api/reports"
        url = url if id is None else url + "/" + id
        r = self._http_get(url)
        if id is None:
            reports = parse_raw_as(List[api.Report], r.content)
            return [x for x in reports if all(getattr(x, k, None) == v for k, v in kwargs.items())]
        else:
            return parse_raw_as(api.Report, r.content)

    def get_artifacts(self, obj: Union[api.Model, api.Report], prefix: str = '', recursive: bool=False, add_prefix=False) -> List[api.FileEntry]:
        """
        Get artifacts for model or test report

        Args:
            obj: model/test report object
            prefix: object prefix (folder)

        Returns:
            List of files
        """
        if isinstance(obj, api.Model):
            r = self._http_get(f"{self.host}/api/models/{obj.id}/artifacts?prefix={prefix}")
        elif isinstance(obj, api.Report):
            r = self._http_get(f"{self.host}/api/reports/{obj.id}/artifacts?prefix={prefix}")
        else:
            raise NotImplementedError("Artifacts not available for type")
        artifacts = parse_raw_as(List[api.FileEntry], r.content)

        if not recursive:
            if add_prefix:
                for a in artifacts:
                    a.name = prefix + a.name
            return artifacts

        all_artifacts = []
        for a in artifacts:
            if a.mime_type == "folder":
                all_artifacts.extend(self.get_artifacts(obj, prefix=f"{prefix}{a.name}/", recursive=True, add_prefix=add_prefix))
            else:
                if add_prefix:
                    a.name = prefix + a.name
                all_artifacts.append(a)

        return all_artifacts

    def get_application_classification(self, application: api.Application = None,
                                       project: api.Project = None) -> Union[api.Project, List[api.Project]]:
        url = self.host + f"/api/resources/projects/{project.id}/applications/{application.id}/classification"
        if application.type == 1:  # Classification application type
            r = self._http_get(url)
            return parse_raw_as(api.Application, r.content)
        elif application.type == 0:  # Generic application type
            return application
        else:  # Unknow application type
            raise ValueError("Unknown application type")

    def get_application(self, id=None) -> Union[api.Application, List[api.Application]]:
        """
        Get application by id

        Args:
            id:

        Returns:
            application if id is given, otherwise a list of applications
        """
        projects = self.get_project()
        applications = [a for p in projects for a in p.applications if id == a.id]
        if len(applications) == 1:
            return applications[0]
        else:
            return applications

    def get_device(self, id=None):
        url = self.host + "/api/devices"
        url = url if id is None else url + "/" + id
        r = self._http_get(url)
        return parse_raw_as(List[api.Device], r.content)

    def get_project(self, id=None) -> Union[api.Project, List[api.Project]]:
        url = self.host + "/api/resources/projects"
        url = url if id is None else url + "/" + id
        r = self._http_get(url)
        return parse_raw_as(Union[api.Project, List[api.Project]], r.content)

    def get_modeltype(self, id=None, master=False) -> Union[api.ModelType, List[api.ModelType]]:
        """
        Get model type

        Args:
            id:
            master: use master mode

        Returns:

        """
        url = f"{self.host}/api/{'master/' if master else 'resources/'}modeltypes/{id if id else ''}"
        r = self._http_get(url)
        return parse_raw_as(Union[api.ModelType, List[api.ModelType]], r.content)

    def get_reporttype(self, id=None, master=False) -> Union[api.ReportType, List[api.ReportType]]:
        """
        Get report type

        Args:
            id:
            master: use master mode

        Returns:

        """
        url = f"{self.host}/api/{'master/' if master else 'resources/'}reporttypes/{id if id else ''}"
        r = self._http_get(url)
        return parse_raw_as(Union[api.ReportType, List[api.ReportType]], r.content)

    def get_available_model_types(self):
        """
        List all available model types
        """
        r = self._http_get(f"{self.host}/api/models/availabletypes")
        return parse_raw_as(List[api.ModelType], r.content)

    def create(self, obj: Union[Dataset, Tag, api.Model, api.Report], **kwargs):
        if isinstance(obj, Dataset):
            payload = obj.dict(include={"name", "reference", "notes", "locked"}, by_alias=True)
            payload["tagIds"] = [tag.id for tag in obj.tags]
            r = self._http_post(f"{self.host}/api/data/", json=payload)
            return self.get_dataset(r.json()["datasetId"], **kwargs)
        elif isinstance(obj, Tag):
            payload = obj.dict(include={"name", "parent_id"}, by_alias=True, exclude_none=True)
            self._http_post(f"{self.host}/api/resources/tags/", json=payload)

            # TODO: return tag id on api
            parent = self.get_tag(obj.parent_id)
            tag = next(filter(lambda x: x.name == obj.name, (parent.children if isinstance(parent, Tag) else parent)))
            return tag
        elif isinstance(obj, api.Model):
            payload = obj.dict(include={"name", "model_type_id", "application_id",
                                        "settings", "dataset_ids", "tag_ids"}, by_alias=True)
            payload["datasetIds"] = payload.pop("datasets")
            r = self._http_post(f"{self.host}/api/models", json=payload)
            return api.Model.parse_raw(r.content)
        elif isinstance(obj, api.Report):
            payload = obj.dict(include={"name", "parent_id", "parent_type", "report_type_id",
                                        "model_ids", "settings", "dataset_ids", "tag_ids"}, by_alias=True)
            payload["datasetIds"] = payload.pop("datasets")
            payload["modelIds"] = payload.pop("models")
            payload["submitToCloud"] = ("submitToCloud" in kwargs and kwargs["submitToCloud"])

            r = self._http_post(f"{self.host}/api/reports", json=payload)
            report = self.get_report(r.json()["id"])
            return report
        else:
            raise NotImplementedError(f"create not implemented for type {type(obj)}")

    def update(self, obj, master=False):
        if isinstance(obj, Dataset):
            payload = obj.dict(include={"name", "reference", "notes", "locked"})
            payload["tagIds"] = [tag.id for tag in obj.tags]
            self._http_post(f"{self.host}/api/data/{obj.id}", json=payload)
        elif isinstance(obj, Tag):
            payload = obj.dict(include={"name", "parent_id"}, by_alias=True, exclude_none=True)
            self._http_post(f"{self.host}/api/resources/tags/{obj.id}", json=payload)
        elif isinstance(obj, api.ModelType):
            if not master:
                raise PermissionError("Not authorized")
            self._http_post(f"{self.host}/api/master/modeltypes/update", json=obj.dict(by_alias=True))
        elif isinstance(obj, api.ReportType):
            if not master:
                raise PermissionError("Not authorized")
            self._http_post(f"{self.host}/api/master/reporttypes/update", json=obj.dict(by_alias=True))
        else:
            raise NotImplementedError(f"create not implemented for type {type(obj)}")

    def delete(self, obj: Union[Dataset, Tag, api.Model, api.Report, api.SftpUser, api.ReportType, api.ModelType]):
        if isinstance(obj, Dataset):
            self._http_delete(f"{self.host}/api/data/{obj.id}")
        elif isinstance(obj, Tag):
            self._http_delete(f"{self.host}/api/resources/tags/{obj.id}")
        elif isinstance(obj, api.Model):
            self._http_delete(f"{self.host}/api/models/{obj.id}")
        elif isinstance(obj, api.Report):
            self._http_delete(f"{self.host}/api/reports/{obj.id}")
        elif isinstance(obj, api.SftpUser):
            self._http_delete(f"{self.host}/api/data/{obj.folder}/sftp/{obj.user_name}")
        elif isinstance(obj, api.ModelType):
            self._http_delete(f"{self.host}/api/resources/modeltypes/{obj.id}")
        elif isinstance(obj, api.ReportType):
            self._http_delete(f"{self.host}/api/resources/reporttypes/{obj.id}")
        else:
            raise NotImplementedError(f"delete not implemented for type {type(obj)}")

    def update_dataset_permission(self, id, user_id, group_id=None, permission_type="Editor"):
        """
        Update dataset permissions for user

        Args:
            id:
            user_id:
            group_id:
            permission_type:

        Returns:

        """
        payload = {"groupId": group_id, "userId": user_id, "resourceId": id, "objectType": 0,
                   "permissionType": permission_type}
        r = self._http_post(self.host + "/api/admin/datasets/" + id + "/permissions", json=payload)
        return r

    def get_dataset_sts_assume_role_response(self, guid):
        cred = self._http_get(f"{self.host}/api/data/{guid}/securitycredentials")
        return cred.text

    def get_schema(self, obj: Union[api.ModelType, api.ReportType]):
        """
        Get schema for a certain model type

        Args:
            obj: modeltype or report type

        Returns:

        """
        r = self._http_get(obj.settings_schema_path, headers={})
        return r.json()

    def get_userinfo(self):
        """
        Get info on user
        """
        url = self.host + "/api/manage/index"
        r = self._http_get(url)
        return api.User.parse_raw(r.content)

    def get_sftp_users(self, dataset, **kwargs) -> List[api.SftpUser]:
        r = self._http_get(f"{self.host}/api/data/{dataset.id}/sftp", **kwargs)
        users = parse_raw_as(List[api.SftpUser], r.content)
        for user in users:
            user.folder = user.folder or dataset.id
        return users

    def create_sftp_user(self, dataset, **kwargs) -> api.SftpUser:
        r = self._http_post(f"{self.host}/api/data/{dataset.id}/sftp", **kwargs)
        return api.SftpUser.parse_raw(r.content)

    def download_url(self, url, dst=None, **kwargs):
        if kwargs.get("headers") is not None:
            log.warning("Headers not supported")

        if url.startswith("/api/"):
            url = self.host + url

        content = self.io.read_file(url, **kwargs)
        if dst is None:
            return content

        if os.path.isdir(dst):
            fname = os.path.basename(unquote(urlparse(url).path))
            dst = os.path.join(dst, fname)
        else:
            if os.path.dirname(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)

        with open(dst, 'wb') as f:
            f.write(content)

        return dst
