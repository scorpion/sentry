from sentry.testutils import APITestCase, SnubaTestCase
from sentry.testutils.helpers.datetime import iso_format, before_now


class GroupTagsTest(APITestCase, SnubaTestCase):
    def test_simple(self):
        event1 = self.store_event(
            data={
                "fingerprint": ["group-1"],
                "tags": {"foo": "bar", "biz": "baz"},
                "release": "releaseme",
                "timestamp": iso_format(before_now(minutes=1)),
            },
            project_id=self.project.id,
        )
        self.store_event(
            data={
                "fingerprint": ["group-1"],
                "tags": {"foo": "quux"},
                "release": "releaseme",
                "timestamp": iso_format(before_now(minutes=1)),
            },
            project_id=self.project.id,
        )

        self.store_event(
            data={
                "fingerprint": ["group-2"],
                "tags": {"abc": "xyz"},
                "timestamp": iso_format(before_now(minutes=1)),
            },
            project_id=self.project.id,
        )

        self.login_as(user=self.user)

        url = f"/api/0/issues/{event1.group.id}/tags/"
        response = self.client.get(url, format="json")
        assert response.status_code == 200, response.content
        assert len(response.data) == 4

        data = sorted(response.data, key=lambda r: r["key"])
        assert data[0]["key"] == "biz"
        assert len(data[0]["topValues"]) == 1

        assert data[1]["key"] == "foo"
        assert len(data[1]["topValues"]) == 2

        assert data[2]["key"] == "level"
        assert len(data[2]["topValues"]) == 1

        assert data[3]["key"] == "release"  # Formatted from sentry:release
        assert len(data[3]["topValues"]) == 1

        # Use the key= queryparam to grab results for specific tags
        url = f"/api/0/issues/{event1.group.id}/tags/?key=foo&key=sentry:release"
        response = self.client.get(url, format="json")
        assert response.status_code == 200, response.content
        assert len(response.data) == 2

        data = sorted(response.data, key=lambda r: r["key"])

        assert data[0]["key"] == "foo"
        assert len(data[0]["topValues"]) == 2
        assert {v["value"] for v in data[0]["topValues"]} == {"bar", "quux"}

        assert data[1]["key"] == "release"
        assert len(data[1]["topValues"]) == 1

    def test_invalid_env(self):
        this_group = self.create_group()
        self.login_as(user=self.user)
        url = f"/api/0/issues/{this_group.id}/tags/"
        response = self.client.get(url, {"environment": "notreal"}, format="json")
        assert response.status_code == 404

    def test_valid_env(self):
        event = self.store_event(
            data={
                "tags": {"foo": "bar", "biz": "baz"},
                "environment": "prod",
                "timestamp": iso_format(before_now(minutes=1)),
            },
            project_id=self.project.id,
        )
        group = event.group

        self.login_as(user=self.user)
        url = f"/api/0/issues/{group.id}/tags/"
        response = self.client.get(url, {"environment": "prod"}, format="json")
        assert response.status_code == 200
        assert len(response.data) == 4
        assert {tag["key"] for tag in response.data} == {
            "foo", "biz", "environment", "level"
        }

    def test_multi_env(self):
        min_ago = before_now(minutes=1)
        env = self.create_environment(project=self.project, name="prod")
        env2 = self.create_environment(project=self.project, name="staging")
        self.store_event(
            data={
                "fingerprint": ["put-me-in-group1"],
                "timestamp": iso_format(min_ago),
                "environment": env.name,
                "tags": {"foo": "bar"},
            },
            project_id=self.project.id,
        )
        event2 = self.store_event(
            data={
                "fingerprint": ["put-me-in-group1"],
                "timestamp": iso_format(min_ago),
                "environment": env2.name,
                "tags": {"biz": "baz"},
            },
            project_id=self.project.id,
        )

        self.login_as(user=self.user)
        url = f"/api/0/issues/{event2.group.id}/tags/"
        response = self.client.get(
            f"{url}?environment={env.name}&environment={env2.name}", format="json"
        )
        assert response.status_code == 200
        assert {tag["key"] for tag in response.data} >= {"biz", "environment", "foo"}
