from email.message import Message
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.request
import urllib.response
import urllib.robotparser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sync_venues as collector


class VenueFetchTests(unittest.TestCase):
    def redirected_fetch(self, destination, delay=None, robots=None):
        visited = []
        destinations = destination if isinstance(destination, list) else [destination]
        class FixtureHTTPS(urllib.request.HTTPSHandler):
            def https_open(self, request):
                visited.append(request.full_url)
                headers = Message()
                if len(visited) <= len(destinations):
                    headers['Location'] = destinations[len(visited) - 1]
                    response = urllib.response.addinfourl(io.BytesIO(b''), headers, request.full_url, 302)
                    response.msg = 'Found'
                else:
                    response = urllib.response.addinfourl(io.BytesIO(b'verified fixture'), headers, request.full_url, 200)
                    response.msg = 'OK'
                return response
        build_opener = urllib.request.build_opener
        def fixture_opener(*handlers):
            return build_opener(FixtureHTTPS(), *handlers)
        self.visited = visited
        with patch.object(urllib.request, 'build_opener', side_effect=fixture_opener), patch.object(collector.time, 'sleep') as sleep:
            self.sleep = sleep
            options = {}
            if delay is not None:
                options['redirect_delay'] = delay
            if robots is not None:
                options['robots'] = robots
            return collector.fetch(collector.BASE + '/old/', **options)

    def test_unexpected_host_redirect_is_rejected_before_following(self):
        with self.assertRaises(ValueError):
            self.redirected_fetch('https://unexpected.example/target/')
        self.assertEqual([collector.BASE + '/old/'], self.visited)
        self.sleep.assert_not_called()

    def test_same_source_https_redirect_still_succeeds(self):
        self.assertEqual('verified fixture', self.redirected_fetch(collector.BASE + '/current/'))
        self.assertEqual([collector.BASE + '/old/', collector.BASE + '/current/'], self.visited)
        self.sleep.assert_called_once_with(10)

    def test_same_source_redirect_honors_effective_robots_delay(self):
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(['User-agent: *', 'Allow: /', 'Crawl-delay: 60'])
        self.assertEqual('verified fixture', self.redirected_fetch(collector.BASE + '/current/', delay=60, robots=robots))
        self.sleep.assert_called_once_with(60)

    def test_same_source_robots_disallowed_redirect_never_waits_or_follows(self):
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(['User-agent: *', 'Disallow: /blocked/'])
        with self.assertRaisesRegex(RuntimeError, 'Robots denies redirect'):
            self.redirected_fetch(collector.BASE + '/blocked/', delay=60, robots=robots)
        self.assertEqual([collector.BASE + '/old/'], self.visited)
        self.sleep.assert_not_called()

    def test_minimum_delay_applies_before_each_allowed_redirect_hop(self):
        destinations = [collector.BASE + '/intermediate/', collector.BASE + '/current/']
        self.assertEqual('verified fixture', self.redirected_fetch(destinations, delay=2))
        self.assertEqual([10, 10], [call.args[0] for call in self.sleep.call_args_list])
        self.assertEqual([collector.BASE + '/old/', *destinations], self.visited)

    def test_https_downgrade_is_rejected_before_redirect_handler_follows(self):
        handler = collector.SourceRedirectHandler()
        request = urllib.request.Request(collector.BASE + '/old/')
        with patch.object(urllib.request.HTTPRedirectHandler, 'redirect_request') as follow:
            with self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, 'Found', {}, 'http://nocovernightclubs.com/current/')
            follow.assert_not_called()


if __name__ == '__main__':
    unittest.main()
