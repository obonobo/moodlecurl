#!/usr/bin/env python3

from requests import Session
from typing import Dict, Any
from bs4 import BeautifulSoup
import re


class MoodleSession:
    """An authenticated session for Concordia's Moodle portal
    """

    URL_FAS_SAML = "https://fas.concordia.ca/adfs/ls/?SAMLRequest=lZJfS8MwFMW%2FSsl7m%2FSPmwtbYTrEwdSxVR98kWuSukCb1NxU9NvbtYob6MC3cHJ%2F9557uFOEumr4vPU7s1GvrUIfvNeVQd5%2FzEjrDLeAGrmBWiH3gm%2FnNyueRIw3znorbEUOkNMEICrntTUkWC5m5InBKBuNk0mZSpaJcapKOZExTLJElaKMxylLk3ORjc4lCR6Uw46cka5RhyO2amnQg%2FGdxJI4ZGnIzgqW8mTEWfJIgkW3jTbge2rnfYOc0hIwEtYI66SGSAAFWSKtkJJg%2Fu3u0hpsa%2BW2yr1poe43qx%2B%2BtlZW6rjFoFHoUqT7EBKKzfAIQWDU7JrfMBKsvwK80EZq83I6u%2BehCPl1UazD9d22IPl0P4T3Wbj83w5r5UGCh73BKT1sNR3O4rYzsVysbaXFR3BlXQ3%2Bb49xFPeKlmHZl%2FLWYKOELrWShObDhONbyz8B&RelayState=https%3A%2F%2Fmoodle.concordia.ca%2Fmoodle%2Fauth%2Fsaml2%2Flogin.php%3Fwants%26idp%3D56f3be3eabcae573100b88c23d68c53e%26passive%3Doff&SigAlg=http%3A%2F%2Fwww.w3.org%2F2001%2F04%2Fxmldsig-more%23rsa-sha256&Signature=wlcGZg%2BNbPGxuhd4xnpbQDUzOxFXGyzxbNdjqIMyhRMHX6L9JFo5iR5cV34EYH6bun5TusJBpRvSWiif27vab9GK66smHR17q7cb%2BXmBEQcgiXAh72ZDfKYKs47Xq41pgltss1tQBzwkaN%2Fll%2BpTPDgjZBNIGZdtnEqmFBcXPrHsORplz%2FvC8tr7CYOiw3C1R%2FvRV%2FKPyzBHda%2BkdJ%2Bcm3UmbVPhU%2FCw92kQaLzRdQ0V%2Bf0Mq%2BpkVnOKGy%2BKP8pIzw2RWEyYj4czkRaP%2FX6PSlkYXKYGy12NyB%2FYfGZCpN9kfMjbAImc%2BnWSY8QplML0QdbuX3P2%2Fdg2DBvYv4NLZQ%3D%3D&client-request-id=cc2ef1e1-129b-436b-b226-008000000092"
    URL_HOME_PAGE = "https://moodle.concordia.ca/moodle/"
    URL_DASHBOARD = f"{URL_HOME_PAGE}my/"
    URL_SECOND_POST = "https://moodle.concordia.ca:443/moodle/auth/saml2/sp/saml2-acs.php/moodle.concordia.ca"

    def __init__(self, username: str, password: str):
       self.__session = Session()
       self.__username = username
       self.__login(password)

    @property
    def username(self) -> str:
        return self.__username

    @property
    def session(self) -> Session:
        return self.__session

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
        data = self.session.get(MoodleSession.URL_DASHBOARD).text
        soup = BeautifulSoup(data, 'html.parser')
        inputs = soup.find_all('input')
        return {
            'SAMLResponse': inputs[0].get("value"),
            'RelayState': MoodleSession.URL_HOME_PAGE
        }

    @staticmethod
    def __get_course_title(element) -> str:
        COURSE_CODE = re.compile(r'^\w{4}-\d{3}')
        # COURSE_CODE = re.compile(r'.*')
        found = element.find_all('span', text=COURSE_CODE)
        if len(found) < 1:
            return None
        return found[0].text

    def get_courses(self) -> Dict[str, Any]:
        COURSE_URL_PATTERN = re.compile(r'.*/view\.php\?id=\d+')
        dashboard = self.session.get(MoodleSession.URL_DASHBOARD)
        soup = BeautifulSoup(dashboard.text, 'html.parser')
        found = soup.find_all('a', {'href': COURSE_URL_PATTERN})
        filter_course_titles = (
            (element, element['href'], MoodleSession.__get_course_title(element))
            for element in found
        )
        filter_remove_non_courses = (
            element
            for element in filter_course_titles
            if element[2] is not None and isinstance(element[2], str)
        )
        generate_return_dict = {
            course: link
            for (_, link, course) in filter_remove_non_courses
        }
        print(generate_return_dict)


def main() -> None:
    moodle = MoodleSession("username", "password")
    moodle.get_courses()


if __name__ == "__main__":
    main()
