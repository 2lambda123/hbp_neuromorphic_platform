from uuid import UUID
from typing import List
from datetime import date
import logging
import asyncio

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status as status_codes
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..data_models import (
    Project, ProjectSubmission, ProjectStatus, Quota
)
from .. import db, oauth

logger = logging.getLogger("simqueue")

auth = HTTPBearer()
router = APIRouter()


@router.get("/projects/", response_model=List[Project])
async def query_projects(
    status: ProjectStatus = Query(None, description="status"),
    collab_id: List[str] = Query(None, description="collab id"),
    owner_id: List[str] = Query(None, description="owner id"),
    #date_range_start: date = Query(None, description="projects which started after this date"),
    #date_range_end: date = Query(None, description="projects which started before this date"),
    size: int = Query(10, description="Number of projects to return"),
    from_index: int = Query(0, description="Index of the first project to return"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Return a list of projects
    """
    # If the user (from the token) is an admin there are no restrictions on the query
    # If the user is not an admin:
    #   - if owner_id is provided, it must contain _only_ the user's id
    #   - if collab_id is not provided, projects for collabs for which the user has edit access are returned
    #   - if collab_id is provided, the user must have edit access for all collabs in the list
    user = await oauth.User.from_token(token.credentials)
    if not as_admin:
        if owner_id:
            if len(owner_id) > 1:
                raise HTTPException(
                    status_code=status_codes.HTTP_400_BAD_REQUEST,
                    detail="Only admins can directly query projects they don't own, try querying by collab_id"
                )
            elif owner_id[0] != user.username:  # todo: also support user_id_v1
                raise HTTPException(
                    status_code=status_codes.HTTP_403_FORBIDDEN,
                    detail=f"Owner id provided ({owner_id[0]}) does not match authentication token ({user.username})",
                )
        if collab_id:
            for cid in collab_id:
                if not user.can_edit(cid):
                    raise HTTPException(
                        status_code=status_codes.HTTP_403_FORBIDDEN,
                        detail="You do not have permission to view collab {cid}"
                    )
        else:
            collab_id = user.get_collabs(access=["editor", "administrator"])
    elif not user.is_admin:
        raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"The token provided does not give admin privileges"
        )
    projects = await db.query_projects(status, collab_id, owner_id, from_index, size)
    return projects


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: int = Path(..., title="Project ID", description="ID of the project to be retrieved"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Return an individual project
    """
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    get_project_task = asyncio.create_task(db.get_project(project_id))
    user = await get_user_task
    project = await get_project_task
    if (as_admin and user.is_admin) or await user.can_view(project["collab"]):
        return project
    raise HTTPException(
        status_code=status_codes.HTTP_404_NOT_FOUND,
        detail=f"Either there is no project with id {project_id}, or you do not have access to it"
    )


@router.get("/collabs/", response_model=List[str])
async def query_collabs(
    status: ProjectStatus = Query(None, description="status"),
    user_id: List[str] = Query(None, description="user id"),
    size: int = Query(100, description="Number of collabs to return"),
    from_index: int = Query(0, description="Index of the first collab to return"),
    # todo: consider adding an option to filter by projects that have active quotas (accepted, not expired, and remaining quota > 0)
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Return a list of collabs for which the user has edit permissions and a neuromorphic computing project exists
    """
    # If the user (from the token) is an admin there are no restrictions on the query
    # If the user is not an admin:
    #   - if user_id is provided, it must contain _only_ the user's id
    #   - if collab_id is not provided, projects for collabs for which the user has edit access are returned
    #   - if collab_id is provided, the user must have edit access for all collabs in the list
    user = await oauth.User.from_token(token.credentials)
    if not as_admin:
        if user_id:
            if len(user_id) > 1:
                raise HTTPException(
                    status_code=status_codes.HTTP_400_BAD_REQUEST,
                    detail="Only admins can run queries for users other than themselves"
                )
            elif user_id[0] != user.username:  # todo: also support user_id_v1
                raise HTTPException(
                    status_code=status_codes.HTTP_403_FORBIDDEN,
                    detail=f"User id provided ({user_id[0]}) does not match authentication token ({user.username})",
                )
        collab_id = user.get_collabs(access=["editor", "administrator"])
    elif not user.is_admin:
        raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"The token provided does not give admin privileges"
        )
    else:
        # todo: if possible, obtain list of collab memberships for the provided user
        raise HTTPException(
            status_code=status_codes.HTTP_501_NOT_IMPLEMENTED,
            detail=f"This option has not been implemented yet"
        )
    projects = await db.query_projects(status, collab_id, owner_id=None, from_index=from_index, size=size)
    collabs = set(prj["collab"] for prj in projects)
    return sorted(collabs)


@router.get("/projects/{project_id}/quotas/", response_model=List[Project])
async def query_quotas(
    project_id: int = Path(..., title="Project ID", description="ID of the project whose quotas should be retrieved"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    size: int = Query(10, description="Number of projects to return"),
    from_index: int = Query(0, description="Index of the first project to return"),
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Return a list of quotas for a given project
    """
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    get_project_task = asyncio.create_task(db.get_project(project_id))
    user = await get_user_task
    project = await get_project_task
    if not ((as_admin and user.is_admin) or await user.can_view(project["collab"])):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail=f"Either there is no project with id {project_id}, or you do not have access to it"
        )
    quotas = await db.query_quotas(project_id=[project_id], size=size, from_index=from_index)
    return quotas