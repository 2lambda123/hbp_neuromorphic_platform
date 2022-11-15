from uuid import UUID
from typing import List
from datetime import date
import logging
import asyncio
import uuid
from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status as status_codes, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..data_models import (
    Project, ProjectSubmission, ProjectUpdate, ProjectStatus, Quota, QuotaSubmission, QuotaUpdate,
)
from .. import db, oauth

logger = logging.getLogger("simqueue")

auth = HTTPBearer()
router = APIRouter()









 
        
        
                    
def to_dictSerial(project: Project, quotas: List[Quota]):
        
        data = {}
       
        data= project
        data["status"] = Project(**project).status()
        
        data["resource_uri"] = "/projects/"+str(project["id"])
        
       
        quota = None
        
        i = 1
        content=[]
        for quota in quotas:
             
           
                
                 content.append(to_dictSerialQuota(quota, project))
               
                 
       
        
        data["quotas"]= content
        
        return data




def to_dictSerialQuota(quota: Quota, project: Project):
        
        data = {}
        
        data= quota
        
          
        
       
        data["resource_uri"] = "/projects/"+str(project["id"])+"/quotas/"+str(quota["id"])
       
        
         
        return data



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
    size_q: int = Query(10, description="Number of quotas to return"),
    from_index_q: int = Query(0, description="Index of the first quota to return"),
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
    
    projects_with_quotas = []
    for project in projects:
      
       quotas = await db.query_quotas(project['id'],size=size_q, from_index=from_index_q)
       projects_with_quotas= to_dictSerial(project, quotas)
     
    return projects


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(
    
    project_id: UUID = Path(..., title="Project ID", description="ID of the project to be retrieved"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    token: HTTPAuthorizationCredentials = Depends(auth),
    size_q: int = Query(10, description="Number of quotas to return"),
    from_index_q: int = Query(0, description="Index of the first quota to return"),
):
    """
    Return an individual project
    """ 
    user = await oauth.User.from_token(token.credentials)
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    
   
    get_project_task = db.get_project(project_id)
    
    user = await get_user_task
    
    project = await get_project_task
    if project is not None:
       quotas= await db.query_quotas(project['id'], size=size_q, from_index=from_index_q)
       content= to_dictSerial(project, quotas)
       
       if (as_admin and user.is_admin) or await user.can_view(project["collab"]):
            return content
       else:
              raise HTTPException(
              status_code=status_codes.HTTP_403_FORBIDDEN,
              detail=f" You do not have access to this project"
              )
            
    else: 
        raise HTTPException(
        status_code=status_codes.HTTP_404_NOT_FOUND,
        detail=f"There is no project with id {project_id}"
       )
    
    
    
    
@router.delete("/projects/{project_id}", status_code=status_codes.HTTP_200_OK)
async def delete_project(
    
    project_id: UUID = Path(..., title="Project ID", description="ID of the project to be deleted"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Delete an individual project
    """ 
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    
   
    get_project_task = db.get_project(project_id)
    
    user = await get_user_task
    
    project = await get_project_task
    
    
    
    if project is not None: 
    
      try:
         if (as_admin and user.is_admin) or  user.can_edit(project["collab"]):
               
           if query_quotas(project_id) is not None:
               
              await db.delete_quotas_from_project(project_id)
           await db.delete_project(project_id)   
         else:
           raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail=f"You are not allowed to delete this project"
              ) 
      except:
            raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"User Object  has no attribute 'token"
            )          
    else:
        
        raise HTTPException(
        status_code=status_codes.HTTP_404_NOT_FOUND,
        detail=f"Either there is no project with id {project_id}, or you do not have access to it"
      )    
    
@router.delete("/projects/{project_id}/quotas/{quota_id}", status_code=status_codes.HTTP_200_OK)
async def delete_onequota(
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    project_id: UUID = Path(..., title="Project ID", description="ID of the project from which the quota should be removed"),
    quota_id: int = Path(..., title="Quota ID", description="ID of the quota thats should be deleted"),
    
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    """
    Delete an individual project
    """ 
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    
   
    get_project_task = db.get_project(project_id)
    
    user = await get_user_task
    
    project = await get_project_task
    
    
    
    if project is  None: 
      
         raise HTTPException(
           status_code=status_codes.HTTP_404_NOT_FOUND,
           detail=f"Either there is no project with id {project_id}, or you do not have access to it"
          )    
        
       
    if not (as_admin and user.is_admin) :
        raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail=f"You are not allowed to delete quotas from this project"
              )       
          
    if await db.get_quota(quota_id, project_id) is None:
         raise HTTPException(
                  status_code=status_codes.HTTP_404_NOT_FOUND,
                  detail=f"There is no Quota with this id"  
                  )            
             
    await db.query_deleteonequota(quota_id, project_id)
             
   
   
    
        
    
    
    
@router.post("/projects/", status_code=status.HTTP_201_CREATED)
async def create_project(
    projectRB: ProjectSubmission, 
 
    
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
   
    
   
    
    
   
   
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth), ):
    
    
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
   
    user = await get_user_task
    
    
    content = jsonable_encoder(projectRB)
    content['accepted']= False
    if 'submitted' not in content.keys():
        content['submitted']= False
        
    try:
         if not ((as_admin and user.is_admin) or  user.can_edit(content['collab'])):
               
                raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail=f"You do not have permisson de create project in this Collab"
                )
    except:
            raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"User Object  has no attribute 'token"
            )    
        
    
    content['id']= uuid.uuid1()
    content['owner' ]= user.username
   
    await db.post_project(content)
    
    
           


@router.get("/projects/{project_id}/quotas/", response_model=List[Quota])
async def query_quotas(
    project_id: UUID = Path(..., title="Project ID", description="ID of the project whose quotas should be retrieved"),
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    size: int = Query(10, description="Number of quotas to return"),
    from_index: int = Query(0, description="Index of the first quota to return"),
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
    if project is  None: 
      
         raise HTTPException(
           status_code=status_codes.HTTP_404_NOT_FOUND,
           detail=f"Either there is no project with id {project_id}, or you do not have access to it"
    
          ) 
    try:
         if not ((as_admin and user.is_admin) or await user.can_view(project["collab"])):
               
                raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail=f"You Can not view quotas"
                )
    except:
            raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"User Object  has no attribute 'token"
            )       
    
    quotas = await db.query_quotas(project_id, size=size, from_index=from_index)
    
       
       
    
    content=[]
    for quota in quotas:
             
          content.append(to_dictSerialQuota(quota, project))
    
                 
    return content


@router.get("/projects/{project_id}/quotas/{quota_id}", response_model= Quota)
async def query_onequota(
    project_id: UUID = Path(..., title="Project ID", description="ID of the project whose quotas should be retrieved"),
    quota_id: int = Path(..., title="Quota ID", description="ID of the quota thats should be retrieved"),
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
    if project is not None:
       if not ((as_admin and user.is_admin) or await user.can_view(project["collab"])):
            raise HTTPException(
                status_code=status_codes.HTTP_401_UNAUTHORIZED,
                detail=f" You do not have access to it"
             )
        
        
        
       quotas = await db.get_quota(quota_id, project_id)
     
    
    
    else:
      raise HTTPException(
             status_code=status_codes.HTTP_404_NOT_FOUND,
             detail=f"Either there is no project with id {project_id}, or you do not have access to it"
             )
    
    
    if await db.get_quota(quota_id, project_id)is None:
         raise HTTPException(
                  status_code=status_codes.HTTP_404_NOT_FOUND,
                  detail=f"There is no Quota  with this id that belongs to this project"  
                  )
                  
                 
    if quotas is not None:  
            content  = (to_dictSerialQuota(quotas, project))
    
    return  content      
    
    
@router.post("/projects/{project_id}/quotas/", status_code=status_codes.HTTP_201_CREATED)
async def create_quotas(
    quota: QuotaSubmission, 
    project_id: UUID = Path(..., title="Project ID", description="ID of the project whose quotas should be added"),
    
   
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
   
   
   
    
   
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    get_project_task = asyncio.create_task(db.get_project(project_id))
    user = await get_user_task
    project = await get_project_task
    if not ( user.is_admin):
        raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"you don not have permission to create quota"
        )
		
    if project is None:
        raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"you can not  create quota without project"
        )
    await db.post_quotas(project_id, quota)


@router.put("/projects/{project_id}/quotas/{quota_id}", status_code=status_codes.HTTP_200_OK)
async def update_quotas(
    quota: QuotaUpdate,
    quota_id: int, 
    project_id: UUID = Path(..., title="Project ID", description="ID of the project whose quotas should be added"),
    
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
   
    
    get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
    get_project_task = asyncio.create_task(db.get_project(project_id))
	
    user = await get_user_task
    if get_project_task is None:
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail=f"Project not found"
        )
	 
    quota_old= await db.get_quota(quota_id, project_id)
    
    
    
    content = jsonable_encoder(quota)
    if not (as_admin and user.is_admin):
        raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"you don not have permission to update quota"
        )
    if quota_old is  None: 
      
         raise HTTPException(
           status_code=status_codes.HTTP_404_NOT_FOUND,
           detail=f"No Quota to change"
          )  
    
    if content is  None: 
      
         raise HTTPException(
           status_code=status_codes.HTTP_404_NOT_FOUND,
           detail=f"No content to change"
          )  
    
    
       
    await db.put_quotas(project_id, content, quota_id) 
     
    
@router.get("/collabs/", response_model=List[str])
async def query_collabs(
    status: ProjectStatus = Query(None, description="project status"), 
    user_id: List[str] = Query(None, description="user id"),
    size: int = Query(10, description="Number of collabs to return"),
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
async def update_project(projectRB: ProjectUpdate,     project_id: UUID = Path(..., title="Project ID", description="ID of the project to be retrieved"),
    
   
    
    as_admin: bool = Query(False, description="Run this query with admin privileges, if you have them"),

    token: HTTPAuthorizationCredentials = Depends(auth), ):
    
      
    
      get_user_task = asyncio.create_task(oauth.User.from_token(token.credentials))
      get_project_task = asyncio.create_task(db.get_project(project_id))
      user = await get_user_task
      project = await get_project_task
     
      content = jsonable_encoder(projectRB)
     
      try:
         if not ((as_admin and user.is_admin) or  user.can_edit(project["collab"])):
               
                raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to modify this project."
                )
      except:
            raise HTTPException(
            status_code=status_codes.HTTP_403_FORBIDDEN,
            detail=f"User Object  has no attribute 'token"
            )       
      new_status= content['status']      
      if new_status in ('accepted', 'rejected'):
            logger.info("Changing status")
            if not (as_admin and user.is_admin):
                raise HTTPException(
                status_code=status_codes.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to change the status of this project."
             )
          
            current_status = Project(**project).status()
            content['owner']=project['owner']
      
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
               
            if project["submission_date"] is  not None:
                raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Can't edit a submitted form."
                
              )
            
                 
            if  content['submitted'] is True:
                          project['submission_date'] = date.today() 
                 
            for field, value in project.items():
               
                
                if field not in content.keys():
                   
                   content[field] = value                        
            await db.put_project(project_id, content )
            logger.info("Updating project")
            return status.HTTP_201_CREATED

    