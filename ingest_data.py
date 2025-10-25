import pandas as pd
import neo4j
from dotenv import load_dotenv
import os
from tqdm import tqdm
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Loading data...")



# Set up Neo4j connection
load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

try:
    driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
    print("Connected to Neo4j instance successfully!")
except Exception as e:
    print(f"Failed to connect to Neo4j: {e}")


def ingest_user(session, name, user_id):
    """
    Inserta un usuario usando MERGE para evitar duplicados
    """
    query = """
    MERGE (u:User {id: $user_id})
    SET u.name = $name
    RETURN u
    """
    try:
        result = session.run(query, user_id=user_id, name=name)
        record = result.single()
        return True
    except Exception as e:
        logger.error(f"Error creating user {name}: {str(e)}")
        return False

def process_users_file(session, filename="users.txt"):
    """
    Lee el archivo de usuarios y los ingresa a Neo4j
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        added_count = 0
        error_count = 0
        
        print(f"📖 Processing {len(lines)} lines from {filename}...")
        
        for line in tqdm(lines, desc="Adding users"):
            line = line.strip()
            if not line or line.startswith('#'):  # Saltar líneas vacías o comentarios
                continue
                
            try:
                # Dividir por coma
                parts = line.split(',')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    user_id = parts[1].strip()
                    
                    # Insertar usuario
                    if ingest_user(session, name, user_id):
                        added_count += 1
                    else:
                        error_count += 1
                else:
                    logger.warning(f"Invalid format in line: {line}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing line '{line}': {e}")
                error_count += 1
        
        print(f" Successfully added/updated: {added_count} users")
        print(f" Errors: {error_count}")
        return added_count, error_count
        
    except FileNotFoundError:
        print(f" File {filename} not found!")
        return 0, 0
    except Exception as e:
        print(f" Error reading file: {e}")
        return 0, 0
    
def ingest_post(session, idp, idu, content):

    query = """
    MERGE (p:Post {idp: $idp})
    SET p.idu = $idu, p.content = $content 
    WITH p
    MATCH (u:User {id:$idu})
    MERGE (u) - [:HAS_POST] -> (p)
    RETURN u
    """
    try:
        result = session.run(query, idp=idp, idu=idu, content=content)
        return True
    except Exception as e:
        logger.error(f"Error creating post {idp}: {str(e)}")
        return False

def process_post_file(session, filename="post.txt"):
    """
    Lee el archivo de posts y los ingresa a Neo4j
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        added_count = 0
        error_count = 0
        
        print(f" Processing {len(lines)} lines from {filename}...")
        
        for line in tqdm(lines, desc="Adding posts"):
            line = line.strip()
            
            if not line or line.startswith('#'):  # Skip comments
                continue
                
            try:
                # Dividir por coma
                parts = line.split(',',2)
                if len(parts) >= 2:
                    idp = parts[0].strip()
                    idu = parts[1].strip()
                    content = parts[2].strip()
                    
                    # Insertar usuario
                    if ingest_post(session, idp, idu,content):
                        added_count += 1
                    else:
                        error_count += 1
                else:
                    logger.warning(f"Invalid format in line: {line}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing line '{line}': {e}")
                error_count += 1
        
        print(f" Successfully added/updated: {added_count} posts")
        print(f" Errors: {error_count}")
        return added_count, error_count
        
    except FileNotFoundError:
        print(f" File {filename} not found!")
        return 0, 0
    except Exception as e:
        print(f"Error reading file: {e}")
        return 0, 0
    
def ingest_comment(session, post_id, author_user_id, comment_id, content, like, authorizer_user_id=None):
    query = """
    MATCH (p:Post {idp: $post_id})
    MATCH (author_user:User {id: $author_user_id})
    
    WITH p, author_user
    WHERE p IS NOT NULL AND author_user IS NOT NULL
    
    MERGE (c:Comment {
        idc: $comment_id,
        idp: $post_id,
        content: $content,
        datec: datetime(),
        like: $like
    })
    MERGE (p)-[:HAS]->(c)
    MERGE (author_user)-[:MAKES]->(c)
    
    WITH c, p, author_user
    
    WHERE $authorizer_user_id IS NOT NULL
    MATCH (authorizer_user:User {id: $authorizer_user_id})
    MERGE (authorizer_user)-[:AUTHORIZES]->(c)
    SET c.datea = datetime()
    
    RETURN c, p, author_user
    """
    
    try:
        result = session.run(query, 
                           post_id=post_id,
                           author_user_id=author_user_id,
                           comment_id=comment_id,
                           content=content,
                           like=like,
                           authorizer_user_id=authorizer_user_id)
        
        record = result.single()
        if record:
            if authorizer_user_id:
                print(f"Comment {comment_id} creado y autorizado para post {post_id}")
            else:
                print(f"Comment {comment_id} creado (pendiente de autorización) para post {post_id}")
            return True
        else:
            print(f" Unable to  create comment {comment_id}: Post {post_id} or User {author_user_id} doesnt exists")
            return False
            
    except Exception as e:
        print(f" Error creating comment {comment_id}: {e}")
        return False
    
def authorize_comment(session, comment_id, authorizer_user_id):
    
    #Authorizes an existent comment
    query = """
    MATCH (c:Comment {idc: $comment_id})
    MATCH (authorizer_user:User {id: $authorizer_user_id})
    MERGE (authorizer_user)-[:AUTHORIZES]->(c)
    SET c.datea = datetime()  
    RETURN c, authorizer_user
    """
    
    try:
        result = session.run(query, 
                           comment_id=comment_id,
                           authorizer_user_id=authorizer_user_id)
        return result.single() is not None
    except Exception as e:
        print(f" Error authorizing comment {comment_id}: {e}")
        return False
    
def process_comment_file(session, filename="comments.txt"):

    #Format: post_id,author_user_id,comment_id,content,like,authorizer_user_id(opcional)

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        added_count = 0
        error_count = 0
        
        print(f"📖 Processing {len(lines)} lines from {filename}...")
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):  # Skip comments
                continue
                
            try:
                # Split by coma
                parts = line.split(',')
                if len(parts) >= 5:
                    idp = parts[0].strip()
                    author_user_id = parts[1].strip()
                    comment_id = parts[2].strip()
                    content = parts[3].strip()
                    
                    # Like to boolean
                    like_str = parts[4].strip().lower()
                    like = like_str in ['true', '1', 'yes', 'si', 'verdadero']
                    
                    # Optional authorizer
                    authorizer_user_id = parts[5].strip() if len(parts) > 5 else None
                    if authorizer_user_id == "":
                        authorizer_user_id = None
                    
                    # Comment insertion
                    if ingest_comment(session, idp, author_user_id, comment_id, content, like, authorizer_user_id):
                        added_count += 1
                    else:
                        error_count += 1
                else:
                    print(f" Invalid format in line: {line}")
                    error_count += 1
                    
            except Exception as e:
                print(f" Error processing line '{line}': {e}")
                error_count += 1
        
        print(f" Successfully added: {added_count} comments")
        print(f" Errors: {error_count}")
        return added_count, error_count
        
    except FileNotFoundError:
        print(f" File {filename} not found!")
        return 0, 0
    except Exception as e:
        print(f" Error reading file: {e}")
        return 0, 0


added = [0,0,0,0]
errors = [0,0,0,0]
def main():
    try:
        with driver.session() as session:
            added[0], errors[0] = process_users_file(session, "users.txt")
            added[1], errors[1] = process_post_file(session, "post.txt")
            added[1], errors[1] = process_comment_file(session, "comments.txt")

    except Exception as e:
        print(f" Error in main: {e}")
    finally:
        driver.close()
        print(" Driver closed.")


if __name__ == "__main__":
    main()
