#!/usr/bin/env python3

from requests import Session
from typing import Dict, Any, List, Generator, Callable
from bs4 import BeautifulSoup
import re
import asyncio
import os
from argparse import ArgumentParser, Namespace
import sys


class Cli:

    ARG_DESCRIPTIONS = {
        'main': {
            'description': "Authenticated CLI access to Concordia's "
                           "online Moodle portal",
            'args': [
                {

                    'flags': ['-u', '--username'],
                    'dest': 'username',
                    'help': 'Username for logging into Moodle',
                },
                {
                    'flags': ['-p', '--password'],
                    'dest': 'password',
                    'help': 'Password for logging into Moodle'
                },
                {
                    'flags': ['--password-stdin'],
                    'dest': 'password_stdin',
                    'action': 'store_true',
                    'default': False,
                    'help': 'Take the password from stdin'
                }
            ]
        },
        'course': {
            'description': "Perform an operation on a specific course",
            'args': [
                {
                    'name': ['']
                }
            ]
        },
        'resources': {
            'description': "Access resources (files) for a course on Moodle",
            'args': [
                {
                    'flags': ['-c', '--course'],
                    'dest': 'course',
                    'help': 'Course ID for to search'
                }
            ]
        }
    }

    class Parser:
        def __init__(
                self,
                command: str = sys.argv[0],
                parent_parser: ArgumentParser = None,
                description: str = None,
                args: List[Dict[str, Any]] = []):

            def init_parser(call_me):
                self.__parser = call_me(command, description=description)

            if not parent_parser:
                init_parser(ArgumentParser)
            else:
                init_parser(parent_parser.add_subparsers().add_parser)

            self.__init_args(args)

        @property
        def parser(self) -> ArgumentParser:
            return self.__parser

        def __init_args(self, args: List[Dict[str, Any]]) -> None:
            for arg in args:
                (_, flags), *rest = arg.items()
                self.parser.add_argument(*flags, **dict(rest))

    def __init__(self):
        self.__main_parser = Cli.Parser(**Cli.ARG_DESCRIPTIONS['main']).parser

        self.__resources_parser = Cli.Parser(
            parent_parser=self.parser,
            command='resources',
            **Cli.ARG_DESCRIPTIONS['resources']).parser

        self.__parsed_args = None

    @property
    def parser(self) -> ArgumentParser:
        return self.__main_parser

    @property
    def args(self) -> Namespace:
        if not self.__parsed_args:
            self.__parsed_args = self.parser.parse_args()
        return self.__parsed_args

    def __repr__(self) -> str:
        return repr(self.parser)


class Decorators:

    @staticmethod
    def tolist(
            gen_func: Callable[..., Generator[Any, None, None]]
            ) -> Callable[..., List[Any]]:
        return lambda *a, **ka: list(gen_func(*a, **ka))

    @staticmethod
    def totask(
            async_func: Callable[..., asyncio.coroutine]
            ) -> Callable[..., asyncio.Task]:
        return lambda *a, **ka: asyncio.create_task(async_func(*a, **ka))


class Resource:
    """Represents a document resource available on the page of a course
    """

    def __init__(self, url, session = Session()):
        self.__url = url
        self.__name = None
        self.__response = None
        self.__session = session

    @property
    def url(self):
        return self.__url

    @property
    def name(self):
        if not self.__name:
            self.__name = self.__parse_file_name_from_headers()
        return self.__name

    @property
    def response(self):
        if not self.__response:
            self.__response = self.__session.get(self.url)
        return self.__response

    @property
    def file(self):
        if not self.__file:
            self.__file = ''
        return self.__file

    @Decorators.totask
    async def download(
            self,
            prefix_dir: str = None,
            filename: str = None) -> int:

        save_as = filename if filename else self.name

        if prefix_dir:
            Resource.__create_dir_if_not_exists(prefix_dir)
            save_as = os.path.join(prefix_dir, save_as)

        bytes_saved = 0
        with open(save_as, 'wb') as fd:
            for chunk in self.response.iter_content(chunk_size=1024*1024*5):
                if (chunk):
                    fd.write(chunk)
                    bytes_saved += len(chunk)

        return bytes_saved

    @staticmethod
    def __create_dir_if_not_exists(dir: str) -> None:
        if not os.path.exists(dir):
            try:
                os.makedirs(dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

    def __parse_file_name_from_headers(self) -> str:
        filename_pattern = re.compile(r'(?<=filename=").*(?=")')
        content_disposition = self.response.headers['Content-Disposition']
        found = filename_pattern.findall(content_disposition)
        return found[0] if len(found) > 0 else None

    def __repr__(self) -> str:
        return f"Resource(url={self.url})"


class Course:
    """Represents a Concordia Moodle course
    """

    RESOURCE_URL_PATTERN = re.compile(r'.*/moodle/mod/resource/view\.php\?id=\d+')
    COURSE_URL_PATTERN = re.compile(r'.*/view\.php\?id=\d+')

    def __init__(self, name='', url='', session = Session()):
        self.__name = name
        self.__url = url
        self.__session = session
        self.__soup = None
        self.__resource_list = None

    @property
    def name(self):
        return self.__name

    @property
    def url(self):
        return self.__url

    @property
    def session(self):
        return self.__session

    @property
    def soup(self):
        if not self.__soup:
            self.__soup = BeautifulSoup(self.session.get(self.url).text, 'html.parser')
        return self.__soup

    @property
    def resources(self):
        if not self.__resource_list:
            self.__resource_list = self.__find_all_resources()
        return self.__resource_list

    def _to_resources(func):
        return lambda self: (
            Resource(url=href, session=self.session)
            for href in func(self))

    @Decorators.tolist
    @_to_resources
    def __find_all_resources(self):
        return (
            a['href'] for a in
            self.soup.find_all('a', {'href': Course.RESOURCE_URL_PATTERN}))

    def get_all_pdfs(self):
        pass

    def __repr__(self):
        return f"Course(name={self.name}, url={self.url})"

    def __str__(self):
        return f"{self.name}: {self.url}"


class MoodleSession:
    """An authenticated session for Concordia's Moodle portal
    """

    URL_FAS_SAML = "https://fas.concordia.ca/adfs/ls/?SAMLRequest=lZJfS8MwFMW%2FSsl7m%2FSPmwtbYTrEwdSxVR98kWuSukCb1NxU9NvbtYob6MC3cHJ%2F9557uFOEumr4vPU7s1GvrUIfvNeVQd5%2FzEjrDLeAGrmBWiH3gm%2FnNyueRIw3znorbEUOkNMEICrntTUkWC5m5InBKBuNk0mZSpaJcapKOZExTLJElaKMxylLk3ORjc4lCR6Uw46cka5RhyO2amnQg%2FGdxJI4ZGnIzgqW8mTEWfJIgkW3jTbge2rnfYOc0hIwEtYI66SGSAAFWSKtkJJg%2Fu3u0hpsa%2BW2yr1poe43qx%2B%2BtlZW6rjFoFHoUqT7EBKKzfAIQWDU7JrfMBKsvwK80EZq83I6u%2BehCPl1UazD9d22IPl0P4T3Wbj83w5r5UGCh73BKT1sNR3O4rYzsVysbaXFR3BlXQ3%2Bb49xFPeKlmHZl%2FLWYKOELrWShObDhONbyz8B&RelayState=https%3A%2F%2Fmoodle.concordia.ca%2Fmoodle%2Fauth%2Fsaml2%2Flogin.php%3Fwants%26idp%3D56f3be3eabcae573100b88c23d68c53e%26passive%3Doff&SigAlg=http%3A%2F%2Fwww.w3.org%2F2001%2F04%2Fxmldsig-more%23rsa-sha256&Signature=wlcGZg%2BNbPGxuhd4xnpbQDUzOxFXGyzxbNdjqIMyhRMHX6L9JFo5iR5cV34EYH6bun5TusJBpRvSWiif27vab9GK66smHR17q7cb%2BXmBEQcgiXAh72ZDfKYKs47Xq41pgltss1tQBzwkaN%2Fll%2BpTPDgjZBNIGZdtnEqmFBcXPrHsORplz%2FvC8tr7CYOiw3C1R%2FvRV%2FKPyzBHda%2BkdJ%2Bcm3UmbVPhU%2FCw92kQaLzRdQ0V%2Bf0Mq%2BpkVnOKGy%2BKP8pIzw2RWEyYj4czkRaP%2FX6PSlkYXKYGy12NyB%2FYfGZCpN9kfMjbAImc%2BnWSY8QplML0QdbuX3P2%2Fdg2DBvYv4NLZQ%3D%3D&client-request-id=cc2ef1e1-129b-436b-b226-008000000092"
    URL_HOME_PAGE = "https://moodle.concordia.ca/moodle/"
    URL_DASHBOARD = f"{URL_HOME_PAGE}my/"
    URL_SECOND_POST = "https://moodle.concordia.ca:443/moodle/auth/saml2/sp/saml2-acs.php/moodle.concordia.ca"

    class Dashboard:
        def __init__(self, text):
            self.__text = text
            self.__soup = BeautifulSoup(text, 'html.parser')

        @property
        def text(self):
            return self.__text

        @property
        def soup(self):
            return self.__soup

    def __init__(self, username: str, password: str):
       self.__session = Session()
       self.__username = username
       self.__dashboard = None
       self.__courses = None
       self.__login(password)

    @property
    def username(self) -> str:
        return self.__username

    @property
    def session(self) -> Session:
        return self.__session

    @property
    def courses(self):
        if not self.__courses:
            self.__courses = self.__get_courses()
        return self.__courses

    @property
    def dashboard(self):
        if not self.__dashboard:
            got = self.session.get(MoodleSession.URL_DASHBOARD)
            self.__dashboard = MoodleSession.Dashboard(got.text)
        return self.__dashboard

    def __login(self, password: str) -> None:
        self.session.post(MoodleSession.URL_FAS_SAML, data={
            "UserName": f"concordia.ca\\{self.username}",
            "Password": password,
            "AuthMethod": "FormsAuthentication"
        })
        self.session.post(
            MoodleSession.URL_SECOND_POST,
            data=self.__parse_data_for_second_post())

    def __parse_data_for_second_post(self) -> Dict[str, str]:
        got = self.session.get(MoodleSession.URL_DASHBOARD)
        inputs = BeautifulSoup(got.text, 'html.parser').find_all('input')
        return {
            'SAMLResponse': inputs[0].get("value"),
            'RelayState': MoodleSession.URL_HOME_PAGE
        }

    @staticmethod
    def __get_course_title(element) -> str:
        COURSE_CODE = re.compile(r'^\w{4}-\d{3}')
        found = element.find_all('span', text=COURSE_CODE)
        if len(found) < 1:
            return None
        return found[0].text

    def _remove_non_courses(gen):
        return lambda self: (
            element
            for element in gen(self)
            if element[2] is not None and isinstance(element[2], str))

    def _generate_courses(gen):
        return lambda self: (
            Course(name=course, url=link, session=self.__session)
            for (_, link, course) in gen(self))

    @Decorators.tolist
    @_generate_courses
    @_remove_non_courses
    def __get_courses(self) -> List[Course]:
        COURSE_URL_PATTERN = re.compile(r'.*/view\.php\?id=\d+')
        found = self.dashboard.soup.find_all('a', {'href': COURSE_URL_PATTERN})
        return (
            (element, element['href'], MoodleSession.__get_course_title(element))
            for element in found)

    def __str__(self):
        return f'Moodle session for user: {self.username}'


async def main() -> None:
    moodle = MoodleSession("", "")
    print(moodle.courses)

    soen363 = next(
        c for c in moodle.courses
        if c.name.lower().startswith('soen-363'))

    resources = soen363.resources
    print(resources)
    print(len(resources))

    def download(r, *args, **kwargs):
        print(f"Downloading {r.name}...")
        return r.download(*args, **kwargs)

    count = await download(resources[0], prefix_dir='downloads')
    print(f'Finished downloading {count} bytes...')

    # asyncio.gather(*(download(r) for r in resources))
    # print(f"Finished downloading {len(resources)} files...")


if __name__ == "__main__":
    cli = Cli()
    print(cli.args)
    # asyncio.run(main())
