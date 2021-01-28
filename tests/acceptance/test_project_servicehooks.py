from sentry.models import ServiceHook
from sentry.testutils import AcceptanceTestCase


class ProjectServiceHooksTest(AcceptanceTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user("foo@example.com")
        self.org = self.create_organization(name="Rowdy Tiger", owner=None)
        self.team = self.create_team(organization=self.org, name="Mariachi Band")
        self.project = self.create_project(organization=self.org, teams=[self.team], name="Bengal")
        self.create_member(user=self.user, organization=self.org, role="owner", teams=[self.team])

        self.login_as(self.user)
        self.list_hooks_path = "/settings/{}/projects/{}/hooks/".format(
            self.org.slug, self.project.slug
        )
        self.new_hook_path = "/settings/{}/projects/{}/hooks/new/".format(
            self.org.slug, self.project.slug
        )

    def test_simple(self):
        with self.feature("projects:servicehooks"):
            self.browser.get(self.list_hooks_path)
            self.browser.wait_until_not(".loading-indicator")
            self.browser.snapshot("project settings - service hooks - empty list")
            # click "New"
            self.browser.click('[data-test-id="new-service-hook"]')

            self.browser.wait_until_not(".loading-indicator")
            assert self.browser.current_url == "{}{}".format(
                self.browser.live_server_url, self.new_hook_path
            )
            self.browser.snapshot("project settings - service hooks - create")
            self.browser.element('input[name="url"]').send_keys("https://example.com/hook")
            # click "Save Changes"
            self.browser.click('form [data-test-id="form-submit"]')

            self.browser.wait_until_not(".loading-indicator")
            assert self.browser.current_url == "{}{}".format(
                self.browser.live_server_url, self.list_hooks_path
            )
            self.browser.snapshot("project settings - service hooks - list with entries")

            hook = ServiceHook.objects.get(project_id=self.project.id)
            assert hook.url == "https://example.com/hook"
            assert not hook.events

            # hopefully click the first service hook
            self.browser.click('[data-test-id="project-service-hook"]')
            self.browser.wait_until_not(".loading-indicator")
            assert self.browser.current_url == "{}{}".format(
                self.browser.live_server_url,
                "/settings/{}/projects/{}/hooks/{}/".format(
                    self.org.slug, self.project.slug, hook.guid
                ),
            )
            self.browser.snapshot("project settings - service hooks - details")
