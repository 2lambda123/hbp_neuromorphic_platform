import logging
import requests
from authlib.integrations.starlette_client import OAuth
import httpx
from httpx import Timeout
from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException, status as status_codes

from . import settings, db


logger = logging.getLogger("simqueue")

oauth = OAuth()

oauth.register(
    name="ebrains",
    server_metadata_url=settings.EBRAINS_IAM_CONF_URL,
    client_id=settings.EBRAINS_IAM_CLIENT_ID,
    client_secret=settings.EBRAINS_IAM_SECRET,
    userinfo_endpoint=f"{settings.HBP_IDENTITY_SERVICE_URL}/userinfo",
    client_kwargs={
        "scope": "openid profile collab.drive clb.drive:read clb.drive:write group team web-origins roles email",
        "trust_env": False,
        "timeout": Timeout(timeout=settings.AUTHENTICATION_TIMEOUT),
    },
)


async def get_collab_info(collab, token):
    """Returns the information of a given collab.
    Parameters:
        - collab (str): The id of the collab to retrieve information from.
        - token (str): The authorization token to access the collab service.
    Returns:
        - dict: A dictionary containing the information of the collab.
    Processing Logic:
        - Construct the URL to the collab service using the collab id.
        - Set the authorization header using the provided token.
        - Make a GET request to the collab service.
        - Convert the response to a JSON object.
        - If the response is a dictionary and contains a "code" key with a value of 404, raise a ValueError.
        - Otherwise, return the response."""
    
    collab_info_url = f"{settings.HBP_COLLAB_SERVICE_URL}collabs/{collab}"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(collab_info_url, headers=headers, timeout=60)
    response = res.json()
    if isinstance(response, dict) and "code" in response and response["code"] == 404:
        raise ValueError("Invalid collab id")
    return response


class User:
    def __init__(self, **kwargs):
        """Initializes an object with given attributes.
        Parameters:
            - kwargs (dict): Dictionary of attributes and their values.
        Returns:
            - None: This function does not return anything.
        Processing Logic:
            - Set attributes using setattr().
            - Loop through key-value pairs.
            - Initialize object with given attributes."""
        
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    async def from_token(cls, token):
        """Purpose:
            This function takes in a token and uses it to retrieve user information from an OAuth server. It then creates an instance of the class using the retrieved user information and the provided token.
        Parameters:
            - token (str): The access token used to retrieve user information from the OAuth server.
        Returns:
            - cls: An instance of the class with the retrieved user information and provided token.
        Processing Logic:
            - Uses the provided token to retrieve user information from the OAuth server.
            - If the token is invalid or expired, an HTTPException is raised.
            - The retrieved user information is used to create an instance of the class.
            - The provided token is added to the user information before creating the instance."""
        
        try:
            user_info = await oauth.ebrains.userinfo(
                token={"access_token": token, "token_type": "bearer"}
            )
        except httpx.HTTPStatusError as err:
            if "401" in str(err):
                if token:
                    message = "Token may have expired"
                else:
                    message = "No token provided"
                raise HTTPException(
                    status_code=status_codes.HTTP_401_UNAUTHORIZED,
                    detail=message,
                )
            else:
                raise
        user_info["token"] = {"access_token": token, "token_type": "bearer"}
        return cls(**user_info)

    def __repr__(self):
        """"Returns a string representation of the User object with the username attribute."
        Parameters:
            - self (User): The User object.
        Returns:
            - str: A string representation of the User object.
        Processing Logic:
            - Returns a string with the username.
            - Uses the f-string method.
            - The string is enclosed in User() format.
            - The username attribute is included."""
        
        return f"User('{self.username}')"

    @property
    def is_admin(self):
        """Checks if the user has admin privileges.
        Parameters:
            - self (object): The user object.
        Returns:
            - boolean: True if the user has admin privileges, False otherwise.
        Processing Logic:
            - Checks if the user can edit the "neuromorphic-platform-admin" group.
            - Returns True if the user has edit access.
            - Returns False if the user does not have edit access."""
        
        return self.can_edit("neuromorphic-platform-admin")

    @property
    def username(self):
        """"Returns the preferred username of the user.
        Parameters:
            - self (object): The user object.
        Returns:
            - str: The preferred username of the user.
        Processing Logic:
            - Returns the preferred username.
            - Based on the user object.
            - Does not modify the object.
            - Only returns the username.""""
        
        return self.preferred_username

    async def can_view(self, collab):
        """Purpose:
            This function checks if a user has permission to view a specific collaboration.
        Parameters:
            - self (type): The user's information.
            - collab (type): The collaboration to be checked.
        Returns:
            - bool: True if the user has permission to view the collaboration, False otherwise.
        Processing Logic:
            - Check team permissions.
            - Check if the collaboration is public.
            - Return True if either check passes, False otherwise.
        Example:
            can_view(self, "example_collab")
            # Returns True if the user has permission to view "example_collab", False otherwise."""
        
        # first of all, check team permissions
        target_team_names = {
            role: f"collab-{collab}-{role}" for role in ("viewer", "editor", "administrator")
        }
        for role, team_name in target_team_names.items():
            if team_name in self.roles["team"]:
                return True
        # if that fails, check if it's a public collab
        try:
            collab_info = await get_collab_info(collab, self.token["access_token"])
        except ValueError:
            return False
        else:
            return collab_info.get("isPublic", False)

    def can_edit(self, collab):
        """"""
        
        target_team_names = {
            role: f"collab-{collab}-{role}" for role in ("editor", "administrator")
        }
        for role, team_name in target_team_names.items():
            if team_name in self.roles["team"]:
                return True

    def get_collabs(self, access=["viewer", "editor", "administrator"]):
        """Get all collaborators with given access.
        Parameters:
            - access (list): List of access levels. Defaults to ["viewer", "editor", "administrator"].
        Returns:
            - list: Sorted list of collaborators with given access.
        Processing Logic:
            - Loop through team access roles.
            - Split team access role into parts.
            - Assert that first part is "collab".
            - Join parts to get collaborator name.
            - Get role from last part.
            - If role is in access list, add collaborator to set.
            - Return sorted list of collaborators."""
        
        collabs = set()
        for team_access in self.roles["team"]:
            parts = team_access.split("-")
            assert parts[0] == "collab"
            collab = "-".join(parts[1:-1])
            role = parts[-1]
            if role in access:
                collabs.add(collab)
        return sorted(collabs)


api_key_header_optional = APIKeyHeader(name="x-api-key", auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=True)


async def _get_provider(api_key):
    """"""
    
    provider_name = db.get_provider(api_key)
    if provider_name:
        return provider_name
    else:
        raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN, detail="Could not validate API key"
        )


async def get_provider(api_key: str = Security(api_key_header)):
    """"""
    
    return await _get_provider(api_key)


async def get_provider_optional(api_key: str = Security(api_key_header_optional)):
    """"""
    
    if api_key:
        return await _get_provider(api_key)
    else:
        return None
