#!/usr/bin/env python3

from requests import Session
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import re


class Resource:
    """Represents a document resource available on the page of a course
    """

    def __init__(self, url, session = Session()):
        self.__url = url
        self.__name = None
        self.__file = None
        self.__request = None
        self.__session = session

    @property
    def url(self):
        return self.__url

    @property
    def name(self):
        if not self.__name:
            self.__name = ''
        return self.__name

    @property
    def request(self):
        if not self.__request:
            self.__request = self.__session.get(self.url)
        return self.__request

    @property
    def file(self):
        if not self.__file:
            self.__file = ''
        return self.__file

    def __repr__(self):
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

    def _to_list(func):
        return lambda self: list(func(self))

    @_to_list
    def __find_all_resources(self):
        return (
            a['href'] for a in
            self.soup.find_all('a', {'href': Course.RESOURCE_URL_PATTERN})
        )

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

    def __get_courses(self) -> List[Course]:
        COURSE_URL_PATTERN = re.compile(r'.*/view\.php\?id=\d+')
        found = self.dashboard.soup.find_all('a', {'href': COURSE_URL_PATTERN})
        filter_course_titles = (
            (element, element['href'], MoodleSession.__get_course_title(element))
            for element in found)

        filter_remove_non_courses = (
            element
            for element in filter_course_titles
            if element[2] is not None and isinstance(element[2], str))

        generate_courses = (
            Course(name=course, url=link, session=self.__session)
            for (_, link, course) in filter_remove_non_courses)

        return list(generate_courses)

    def __str__(self):
        return f'Moodle session for user: {self.username}'


def main() -> None:
    moodle = MoodleSession("", "")
    print(moodle.courses)
    soen363 = next(
        c for c in moodle.courses
        if c.name.lower().startswith('soen-363')
    )
    resources = soen363.resources
    print(resources)

    resource = Resource(url=soen363.resources[0], session=moodle.session)
    print(resource)
    print(resource.request.headers)


if __name__ == "__main__":
    main()
