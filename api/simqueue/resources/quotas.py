from uuid import UUID
from typing import List
from datetime import date
import logging
import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status as status_codes, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..data_models import (
    Project, ProjectSubmission, ProjectStatus, Quota, ProjectN, ProjectI, ProjectSerial, QuotaI
)
from .. import db, oauth

logger = logging.getLogger("simqueue")

auth = HTTPBearer()
router = APIRouter()





def to_dict(project: Project):
        
        data = {}
       
        
        for field in ("id", "collab", "owner", "title", "abstract",
                      "description", "duration", "accepted"):
        
            if getattr(project, field) is not None:            
               data[field] = getattr(project, field)
        if project.start_date is not None:
             data["start_date"] = project.start_date
        else:
             data["start_date"] = None   
        if project.submission_date is not None:
             data["submission_date"] = project.submission_date
        else:
             data["submission_date"] = None    
        if project.decision_date is not None:
             data["decision_date"] = project.decision_date
        else:
             data["decision_date"] = None            
        print('data')  
        print (data)
        print('data')  
         
        return data


             
def to_dictSerial(project: Project, quotas: List[QuotaI]):
        
        data = {}
       
        data= project
        data["status"] = Project(**project).status()
        
        data["resource_uri"] = "/projects/"+str(project["id"])
        
                      
        print('data')  
        print (data)
        print('data')  
        print("********************quota:")
        quota = None
        print(quotas)
        i = 1
        contentQ=[]
        for quota in quotas:
             
           
                
                 contentQ.append(to_dictSerialQuota(quota, project))
                 print(contentQ)
                 
        print(":quota********************") 
        
        data["quotas"]= contentQ
        
        return data




def to_dictSerialQuota(quota: QuotaI, project: Project):
        
        data = {}
        
        
        
          
        data["limit"]= quota["limit"]
        
        data["platform"]=quota["platform"]
        
        data["project"]=quota["project_id"]
       
        data["resource_uri"] = "/projects/"+str(project["id"])+"/quotas/"+str(quota["id"])
       
        data["units"]=quota["units"]
        
        data["usage"]=quota["usage"]              
        print('data')  
        print (data)
        print('data')  
         
        return data



@router.get("/projects/", response_model=List[ProjectSerial])
async def query_projects(
    status: ProjectStatus = Query(None, description="status"),
    collab_id: List[str] = Query(None, description="collab id"),
    owner_id: List[str] = Query(None, description="owner id"),
    #date_range_start: date = Query(None, description="projects which started after this date"),
    #date_range_end: date = Query(None, description="projects which started before this date"),
    size: int = Query(1000, description="Number of projects to return"),
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
    for project in projects:
       quotas= await db.follow_relationships_quotas(project["id"])
       contentR= to_dictSerial(project, quotas)
    
    return projects


@router.get("/projects/{project_id}", response_model=ProjectSerial)
async def get_project(
    
    project_id: UUID = Path(..., title="Project ID", description="ID of the project to be retrieved"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Return an individual project
    """ 
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    
   
    get_project_task = db.get_project(project_id)
    
    user = await get_user_task
    
    project = await get_project_task
    
    quotas= await db.follow_relationships_quotas(project["id"])
    
    
    contentR= to_dictSerial(project, quotas)
   
    if (as_admin and user.is_admin) or await user.can_view(project["collab"]):
        return contentR
    
    raise HTTPException(
        status_code=status_codes.HTTP_404_NOT_FOUND,
        detail=f"Either there is no project with id {project_id}, or you do not have access to it"
    )
    
@router.post("/projects/", response_model=Project)
async def create_item(rollab: str, rtitle: str, rabstract: str, rdescription: str, rowner: str, rduration: int, raccepted: bool,  status: ProjectStatus = Query(None, description="status"),
 
 
    submitted: bool = Query(False, description="Submitted Project state"),
    
    collab_id: List[str] = Query(None, description="collab id"),
    owner_id: List[str] = Query(None, description="owner id"),
   
    #date_range_start: date = Query(None, description="projects which started after this date"),
    #date_range_end: date = Query(None, description="projects which started before this date"),
   
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
   
   
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth), ):
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
   
    user = await get_user_task
    
    if not ((as_admin and user.is_admin) or await user.can_view(rcollab)):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail=f"You can not create a project"
        )
    project_id = uuid.uuid1();
    detail=f"id project {project_id}"
    project = await db.post_project(project_id,  rcollab, rtitle, rabstract, rdescription, rowner, rduration, raccepted, submitted)
      
      
    return project

   
           


@router.get("/projects/{project_id}/quotas/", response_model=List[Quota])
async def query_quotas(
    project_id: UUID = Path(..., title="Project ID", description="ID of the project whose quotas should be retrieved"),
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
@router.post("/projects/{project_id}/quotas/", status_code=status_codes.HTTP_200_OK)
async def create_quotas(
    units: str, limit: float, usage: float, platform: str,    project_id: UUID = Path(..., title="Project ID", description="ID of the project whose quotas should be added"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    size: int = Query(10, description="Number of projects to return"),
    from_index: int = Query(0, description="Index of the first project to return"),
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
   
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    get_project_task = asyncio.create_task(db.get_project(project_id))
    user = await get_user_task
    project = await get_project_task
    if not ((as_admin and user.is_admin) or await user.can_view(project["collab"])):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail=f"Either there is no project with id {project_id}, or you do not have access to it"
        )
    await db.post_quotas(project_id, units, limit, usage, platform)
    
    
    
@router.get("/collabs/", response_model=List[str])
async def query_collabs(
    status: ProjectStatus, 
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
    
    
    
    
    

    

@router.put("/projects/{project_id}" , status_code=status_codes.HTTP_200_OK)
async def update_item(projectR: Project,  raccepted: bool,  new_status: ProjectStatus= Query(None, description="status"),  project_id: UUID = Path(..., title="Project ID", description="ID of the project to be retrieved"),
    collab_id: List[str] = Query(None, description="collab id"),
    owner_id: List[str] = Query(None, description="owner id"),
    submitted: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    #date_range_start: date = Query(None, description="projects which started after this date"),
    #date_range_end: date = Query(None, description="projects which started before this date"),
   
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    
   
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth), ):
    
      
      
      get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
      get_project_task = asyncio.create_task(db.get_project(project_id))
      user = await get_user_task
      project = await get_project_task
      data= dict(projectR)
      contentR = to_dict(projectR)
      print('loop*****************:')
      for field, value in project.items():
               
                print('loop*entrance!!!!:') 
                print(contentR.keys())
                if field not in contentR.keys():
                   print(field)
                   print(value)
                   contentR[field] = value
      print('loop************')              
      projectt= {"id": project_id, **projectR.dict()}
      if not ((as_admin and user.is_admin) or  user.can_edit(project["collab"])):
               
                raise HTTPException(
                status_code=status_codes.HTTP_403_NOT_FOUND,
                detail=f"You do not have permission to modify this project."
             )
      if new_status is not None:
            logger.info("Changing status")
            if not (as_admin and user.is_admin):
                raise HTTPException(
                status_code=status_codes.HTTP_403_NOT_FOUND,
                detail=f"You do not have permission to change the status of this project."
             )
          
            current_status = Project(**project).status()
           
      
            if new_status == current_status :
                raise HTTPException(
                status_code=status_codes.HTTP_204_NO_CONTENT,
                detail=f"Same Status"
             )
            elif new_status in ('accepted', 'rejected'):
                   project["decision_date"] = date.today()
                   
                   if new_status == 'accepted':
                      project["start_date"] = project["decision_date"]
                      project["accepted"] = True
                     
                   await db.put_project(project_id, project)
                   
                   status_code=status_codes.HTTP_201_CREATED
                   return status_code
            
            
            else:
                   raise HTTPException(
                    status_code=status_codes.HTTP_400_BAD_REQUEST,
                    detail="Status can only be changed to 'accepted' or 'rejected'"
                  )
            
            
      else:
           
            
            if project is None:
                raise HTTPException(
                status_code=status_codes.HTTP_404_NOT_FOUND,
                detail=f"Project Not Found"
            )
            
                
            if project["submission_date"] is not None:
                raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Can't edit a submitted form."
                
              )
            
                 
            if  submitted is True:
                             contentR[submission_date] = date.today()        
            await db.put_project(project_id, contentR )
            logger.info("Updating project")
            return status.HTTP_201_CREATED
           
            """
            else:
                    raise HTTPException(
                    status_code=status_codes.HTTP_400_BAD_REQUEST,
                    detail=f"BAD REQUEST" 
                    )
            """

    
