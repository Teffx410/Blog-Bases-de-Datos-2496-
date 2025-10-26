import neo4j
from dotenv import load_dotenv
import os
from datetime import datetime
import uuid

# Connection configuration
load_dotenv()
uri = "neo4j+s://189d458e.databases.neo4j.io"
user = "neo4j"
password = "UeFXV5g_Zc8guNdabzDGNe_IlmpI7TAR3C2ZzBGptJM"

try:
    driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
    print("Connected to Neo4j successfully!")
except Exception as e:
    print(f"Connection error: {e}")
    exit(1)

# =============================================================================
# ID GENERATION FUNCTIONS
# =============================================================================
def generate_user_id(session):
    """Generate automatic user ID"""
    query = "MATCH (u:User) RETURN COUNT(u) as user_count"
    result = session.run(query)
    record = result.single()
    user_count = record["user_count"] if record else 0
    return str(user_count + 1)

def generate_post_id(session):
    """Generate automatic post ID"""
    query = "MATCH (p:Post) RETURN COUNT(p) as post_count"
    result = session.run(query)
    record = result.single()
    post_count = record["post_count"] if record else 0
    return f"P{post_count + 1:03d}"  # Formato: P001, P002, etc.

def generate_comment_id(session):
    """Generate automatic comment ID"""
    query = "MATCH (c:Comment) RETURN COUNT(c) as comment_count"
    result = session.run(query)
    record = result.single()
    comment_count = record["comment_count"] if record else 0
    return f"C{comment_count + 1:03d}"  # Formato: C001, C002, etc.

# =============================================================================
# FILE MANAGEMENT FUNCTIONS
# =============================================================================
def save_to_file_preserve_comments(filename, line):
    """Guarda una nueva línea preservando comentarios y formato"""
    try:
        # Si el archivo no existe, crearlo con la línea
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(line + '\n')
            print(f"Data saved to {filename}")
            return True
        
        # Leer todas las líneas existentes
        with open(filename, 'r', encoding='utf-8') as file:
            existing_lines = file.readlines()
        
        # Separar comentarios y datos
        comment_lines = []
        data_lines = []
        
        for existing_line in existing_lines:
            stripped_line = existing_line.strip()
            if stripped_line.startswith('#'):
                comment_lines.append(existing_line)
            elif stripped_line:  # Línea de datos no vacía
                data_lines.append(existing_line)
        
        # Agregar la nueva línea de datos
        data_lines.append(line + '\n')
        
        # Escribir de vuelta: comentarios + datos
        with open(filename, 'w', encoding='utf-8') as file:
            file.writelines(comment_lines)
            if comment_lines and data_lines:  # Salto de línea entre comentarios y datos
                file.write('\n')
            file.writelines(data_lines)
        
        print(f"Data saved to {filename}")
        return True
        
    except Exception as e:
        print(f"Error saving to file: {e}")
        return False

def clean_files_preserve_comments():
    """Limpia los archivos .txt preservando comentarios"""
    files = ["users.txt", "post.txt", "comments.txt"]
    
    for filename in files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    lines = file.readlines()
                
                # Separar comentarios y datos
                comment_lines = []
                data_lines = []
                
                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line.startswith('#'):
                        comment_lines.append(line)
                    elif stripped_line:  # Línea de datos no vacía
                        # Asegurar que tenga salto de línea
                        clean_line = line if line.endswith('\n') else line + '\n'
                        data_lines.append(clean_line)
                
                # Escribir de vuelta
                with open(filename, 'w', encoding='utf-8') as file:
                    file.writelines(comment_lines)
                    if comment_lines and data_lines:  # Salto entre comentarios y datos
                        file.write('\n')
                    file.writelines(data_lines)
                
                print(f"Cleaned {filename} (preserved {len(comment_lines)} comments)")
                
            except Exception as e:
                print(f"Error cleaning {filename}: {e}")

def create_files_if_not_exist():
    """Creates .txt files if they don't exist with proper headers"""
    files = {
        "users.txt": "# Format: name,id\n\n",
        "post.txt": "# Format: post_id,user_id,content\n\n", 
        "comments.txt": "# Format: post_id,author_user_id,comment_id,content,like,authorizer_user_id\n\n"
    }
    
    for filename, header in files.items():
        if not os.path.exists(filename):
            try:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(header)
                print(f"File {filename} created successfully with header")
            except Exception as e:
                print(f"Error creating {filename}: {e}")

# =============================================================================
# 1. USER MANAGEMENT FUNCTIONS
# =============================================================================
def insert_user_interactive(session):
    print("\n=== ADD NEW USER ===")
    
    try:
        # Generar ID automáticamente
        user_id = generate_user_id(session)
        name = input("User name: ").strip()
        
        if not name:
            print("Error: Name is required")
            return False
            
        query = """
        MERGE (u:User {id: $user_id})
        SET u.name = $name
        RETURN u
        """
        
        result = session.run(query, user_id=user_id, name=name)
        record = result.single()
        
        if record:
            # Save to users.txt file
            line = f"{name},{user_id}"
            if save_to_file_preserve_comments("users.txt", line):
                print(f"User '{name}' created successfully with auto-generated ID: {user_id}")
            return True
        else:
            print("Error creating user")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def edit_user_interactive(session):
    """Edit an existing user"""
    print("\n=== EDIT USER ===")
    
    try:
        user_id = input("Enter user ID to edit: ").strip()
        if not user_id:
            print("Error: User ID is required")
            return False
        
        # Check if user exists
        check_query = "MATCH (u:User {id: $user_id}) RETURN u"
        check_result = session.run(check_query, user_id=user_id)
        if not check_result.single():
            print(f"Error: User {user_id} not found")
            return False
        
        new_name = input("Enter new name: ").strip()
        if not new_name:
            print("Error: New name is required")
            return False
        
        query = """
        MATCH (u:User {id: $user_id})
        SET u.name = $new_name
        RETURN u
        """
        
        result = session.run(query, user_id=user_id, new_name=new_name)
        if result.single():
            # Update users.txt file
            update_user_in_file(user_id, new_name)
            print(f"User {user_id} updated successfully")
            return True
        else:
            print("Error updating user")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def delete_user_interactive(session):
    """Delete a user and all their posts and comments"""
    print("\n=== DELETE USER ===")
    
    try:
        user_id = input("Enter user ID to delete: ").strip()
        if not user_id:
            print("Error: User ID is required")
            return False
        
        # Confirm deletion
        confirm = input(f"WARNING: This will delete user {user_id} and ALL their posts and comments. Continue? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'si', 'sí']:
            print("Deletion cancelled")
            return False
        
        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_POST]->(p:Post)
        OPTIONAL MATCH (p)-[:HAS]->(c:Comment)
        DETACH DELETE u, p, c
        RETURN count(u) as deleted_count
        """
        
        result = session.run(query, user_id=user_id)
        record = result.single()
        
        if record and record["deleted_count"] > 0:
            # Remove from users.txt
            remove_user_from_file(user_id)
            print(f"User {user_id} and all associated data deleted successfully")
            return True
        else:
            print(f"Error: User {user_id} not found")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 2. POST MANAGEMENT FUNCTIONS
# =============================================================================
def insert_post_interactive(session):
    print("\n=== ADD NEW POST ===")
    
    try:
        # Generar ID automáticamente
        post_id = generate_post_id(session)
        user_id = input("Author user ID: ").strip()
        content = input("Post content: ").strip()
        
        if not user_id or not content:
            print("Error: User ID and content are required")
            return False
            
        query = """
        MATCH (u:User {id: $user_id})
        MERGE (p:Post {idp: $post_id})
        SET p.idu = $user_id, p.content = $content
        MERGE (u)-[:HAS_POST]->(p)
        RETURN p, u
        """
        
        result = session.run(query, post_id=post_id, user_id=user_id, content=content)
        record = result.single()
        
        if record:
            # Save to posts.txt file
            line = f"{post_id},{user_id},{content}"
            if save_to_file_preserve_comments("post.txt", line):
                print(f"Post created successfully with auto-generated ID: {post_id} for user {user_id}")
            return True
        else:
            print(f"Error: Could not create post. Verify that user {user_id} exists")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def edit_post_interactive(session):
    """Edit an existing post"""
    print("\n=== EDIT POST ===")
    
    try:
        post_id = input("Enter post ID to edit: ").strip()
        if not post_id:
            print("Error: Post ID is required")
            return False
        
        # Check if post exists
        check_query = "MATCH (p:Post {idp: $post_id}) RETURN p"
        check_result = session.run(check_query, post_id=post_id)
        if not check_result.single():
            print(f"Error: Post {post_id} not found")
            return False
        
        new_content = input("Enter new content: ").strip()
        if not new_content:
            print("Error: New content is required")
            return False
        
        query = """
        MATCH (p:Post {idp: $post_id})
        SET p.content = $new_content
        RETURN p
        """
        
        result = session.run(query, post_id=post_id, new_content=new_content)
        if result.single():
            # Update post.txt file
            update_post_in_file(post_id, new_content)
            print(f"Post {post_id} updated successfully")
            return True
        else:
            print("Error updating post")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def delete_post_interactive(session):
    """Delete a post and all its comments"""
    print("\n=== DELETE POST ===")
    
    try:
        post_id = input("Enter post ID to delete: ").strip()
        if not post_id:
            print("Error: Post ID is required")
            return False
        
        # Confirm deletion
        confirm = input(f"WARNING: This will delete post {post_id} and ALL its comments. Continue? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'si', 'sí']:
            print("Deletion cancelled")
            return False
        
        query = """
        MATCH (p:Post {idp: $post_id})
        OPTIONAL MATCH (p)-[:HAS]->(c:Comment)
        DETACH DELETE p, c
        RETURN count(p) as deleted_count
        """
        
        result = session.run(query, post_id=post_id)
        record = result.single()
        
        if record and record["deleted_count"] > 0:
            # Remove from post.txt and comments.txt
            remove_post_from_files(post_id)
            print(f"Post {post_id} and all associated comments deleted successfully")
            return True
        else:
            print(f"Error: Post {post_id} not found")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 3. COMMENT MANAGEMENT FUNCTIONS
# =============================================================================
def insert_comment_interactive(session):
    print("\n=== ADD NEW COMMENT ===")
    
    try:
        # Generar ID automáticamente
        comment_id = generate_comment_id(session)
        post_id = input("Post ID: ").strip()
        author_user_id = input("Comment author user ID: ").strip()
        content = input("Comment content: ").strip()
        
        like_input = input("Did you like the post? (yes/no): ").strip().lower()
        like = like_input in ['yes', 'y', 'true', '1', 'si', 'sí']
        like_str = "true" if like else "false"
        
        authorize = input("Authorize immediately? (yes/no): ").strip().lower()
        authorizer_user_id = ""
        if authorize in ['yes', 'y', 'si', 'sí']:
            authorizer_user_id = input("Authorizer user ID (post owner): ").strip()
        
        if not all([post_id, author_user_id, content]):
            print("Error: Post ID, author user ID and content are required")
            return False
            
        query = """
        MATCH (p:Post {idp: $post_id})
        MATCH (author_user:User {id: $author_user_id})
        
        CREATE (c:Comment {
            idc: $comment_id,
            idp: $post_id,
            content: $content,
            datec: datetime(),
            like: $like
        })
        CREATE (p)-[:HAS]->(c)
        CREATE (author_user)-[:MAKES]->(c)
        
        WITH c
        WHERE $authorizer_user_id IS NOT NULL AND $authorizer_user_id <> ''
        MATCH (authorizer_user:User {id: $authorizer_user_id})
        CREATE (authorizer_user)-[:AUTHORIZES]->(c)
        SET c.datea = datetime()
        
        RETURN c
        """
        
        result = session.run(query, 
                           comment_id=comment_id,
                           post_id=post_id,
                           author_user_id=author_user_id,
                           content=content,
                           like=like,
                           authorizer_user_id=authorizer_user_id)
        
        record = result.single()
        
        if record:
            # Save to comments.txt file
            if authorizer_user_id:
                line = f"{post_id},{author_user_id},{comment_id},{content},{like_str},{authorizer_user_id}"
            else:
                line = f"{post_id},{author_user_id},{comment_id},{content},{like_str},"
            
            if save_to_file_preserve_comments("comments.txt", line):
                if authorizer_user_id:
                    print(f"Comment created successfully with auto-generated ID: {comment_id} (authorized)")
                else:
                    print(f"Comment created successfully with auto-generated ID: {comment_id} (pending authorization)")
            return True
        else:
            print("Error: Could not create comment. Verify that post and user exist")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def edit_comment_interactive(session):
    """Edit an existing comment"""
    print("\n=== EDIT COMMENT ===")
    
    try:
        comment_id = input("Enter comment ID to edit: ").strip()
        if not comment_id:
            print("Error: Comment ID is required")
            return False
        
        # Check if comment exists - usar FIRST() para evitar múltiples resultados
        check_query = """
        MATCH (c:Comment {idc: $comment_id})
        RETURN c
        LIMIT 1
        """
        check_result = session.run(check_query, comment_id=comment_id)
        check_record = check_result.single()
        
        if not check_record:
            print(f"Error: Comment {comment_id} not found")
            return False
        
        new_content = input("Enter new content: ").strip()
        if not new_content:
            print("Error: New content is required")
            return False
        
        # Ask for like status
        like_input = input("Did you like the post? (yes/no): ").strip().lower()
        new_like = like_input in ['yes', 'y', 'true', '1', 'si', 'sí']
        
        # Usar MERGE para actualizar solo el comentario específico
        query = """
        MATCH (c:Comment {idc: $comment_id})
        SET c.content = $new_content, c.like = $new_like
        RETURN c
        """
        
        result = session.run(query, comment_id=comment_id, new_content=new_content, new_like=new_like)
        record = result.single()  # Usar single() para obtener un solo resultado
        
        if record:
            # Update comments.txt file
            update_comment_in_file(comment_id, new_content, new_like)
            print(f"Comment {comment_id} updated successfully")
            return True
        else:
            print("Error updating comment")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def delete_comment_interactive(session):
    """Delete a comment"""
    print("\n=== DELETE COMMENT ===")
    
    try:
        comment_id = input("Enter comment ID to delete: ").strip()
        if not comment_id:
            print("Error: Comment ID is required")
            return False
        
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete comment {comment_id}? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'si', 'sí']:
            print("Deletion cancelled")
            return False
        
        query = """
        MATCH (c:Comment {idc: $comment_id})
        DETACH DELETE c
        RETURN count(c) as deleted_count
        """
        
        result = session.run(query, comment_id=comment_id)
        record = result.single()
        
        if record and record["deleted_count"] > 0:
            # Remove from comments.txt
            remove_comment_from_file(comment_id)
            print(f"Comment {comment_id} deleted successfully")
            return True
        else:
            print(f"Error: Comment {comment_id} not found")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 4. QUERY FUNCTIONS (se mantienen igual)
# =============================================================================
def linked_post_from_user(session, user_id):
    # Verificar si el usuario es manager o anónimo
    if str(user_id) == '999' or str(user_id) == '0':
        print("Manager and anonymous are unable to use this command")
        return []
    
    query = """
    MATCH (p:Post {idu: $user_id})
    RETURN p
    """
    
    try:
        result = session.run(query, user_id=user_id)
        posts_list = []
        
        for record in result:
            post_node = record["p"]
            post_dict = {
                "idp": post_node.get("idp"),
                "idu": post_node.get("idu"), 
                "content": post_node.get("content")
            }
            posts_list.append(post_dict)
        
        return posts_list
        
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
def comments_from_user_post(session):
    try:
        # Step 1: Request user ID
        user_id = input("Enter user ID: ").strip()
        
        if not user_id:
            print("Error: User ID is required")
            return []
        
        # Step 2: Get user's posts
        user_posts = linked_post_from_user(session, user_id)
        
        if not user_posts:
            print(f"No posts found for user {user_id}")
            return []
        
        # Step 3: Show user's posts
        print(f"\nPosts from user {user_id}:")
        print("-" * 50)
        for i, post in enumerate(user_posts, 1):
            print(f"{i}. Post ID: {post['idp']}")
            print(f"   Content: {post['content']}")
            print()
        
        # Step 4: Ask which post to check
        post_choice = input("Enter the number of the post to view comments: ").strip()
        
        try:
            post_index = int(post_choice) - 1
            if post_index < 0 or post_index >= len(user_posts):
                print("Invalid post selection")
                return []
        except ValueError:
            print("Please enter a valid number")
            return []
        
        selected_post = user_posts[post_index]
        post_id = selected_post['idp']
        
        # Step 5: Get comments for the selected post
        query = """
        MATCH (p:Post {idp: $post_id})-[:HAS]->(c:Comment)
        OPTIONAL MATCH (author:User)-[:MAKES]->(c)
        OPTIONAL MATCH (authorizer:User)-[:AUTHORIZES]->(c)
        RETURN c.idc as comment_id,
               c.content as content,
               c.datec as creation_date,
               c.datea as authorization_date,
               c.like as like_status,
               author.id as author_id,
               authorizer.id as authorizer_id
        ORDER BY c.datec
        """
        
        result = session.run(query, post_id=post_id)
        comments_list = []
        
        print(f"\nComments for post '{post_id}':")
        print("=" * 80)
        
        for record in result:
            comment_data = {
                "comment_id": record["comment_id"],
                "content": record["content"],
                "creation_date": record["creation_date"],
                "authorization_date": record["authorization_date"],
                "like_status": bool(record["like_status"]),
                "author_id": record["author_id"],
                "authorizer_id": record["authorizer_id"]
            }
            comments_list.append(comment_data)
            
            # Display formatted output
            like_text = "Me gusta" if comment_data["like_status"] else "No me gusta"
            auth_status = "AUTHORIZED" if comment_data["authorization_date"] else "PENDING"
            
            print(f"Comment ID: {comment_data['comment_id']}")
            print(f"Content: {comment_data['content']}")
            print(f"Created: {comment_data['creation_date']}")
            print(f"Author: {comment_data['author_id']}")
            print(f"Status: {auth_status}")
            
            if comment_data["authorization_date"]:
                print(f"Authorized: {comment_data['authorization_date']}")
                print(f"Authorized by: {comment_data['authorizer_id']}")
            
            print(f"Reaction: {like_text}")
            print("-" * 50)
        
        if not comments_list:
            print("No comments found for this post")
        
        return comments_list
        
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def view_user_posts_interactive(session):
    """Interactive function to view user's posts"""
    try:
        user_id = input("Enter user ID to view posts: ").strip()
        
        if not user_id:
            print("Error: User ID is required")
            return
        
        posts = linked_post_from_user(session, user_id)
        
        if posts:
            print(f"\nPosts from user {user_id}:")
            print("=" * 60)
            for i, post in enumerate(posts, 1):
                print(f"{i}. Post ID: {post['idp']}")
                print(f"   Content: {post['content']}")
                print()
        else:
            print(f"No posts found for user {user_id}")
            
    except Exception as e:
        print(f"Error: {e}")

# =============================================================================
# 5. AUTHORIZATION FUNCTION (se mantiene igual)
# =============================================================================
def authorize_comment_interactive(session):
    """
    Authorizes a comment if the user is the post owner or manager (ID 999)
    """
    print("\n=== AUTHORIZE COMMENT ===")
    
    try:
        comment_id = input("Comment ID to authorize: ").strip()
        authorizer_user_id = input("Authorizer user ID: ").strip()
        
        if not comment_id or not authorizer_user_id:
            print("Error: Both comment ID and authorizer user ID are required")
            return False
        
        # Check if user has permission to authorize (is post owner or manager)
        permission_query = """
        MATCH (c:Comment {idc: $comment_id})-[:HAS]-(p:Post)
        WHERE p.idu = $authorizer_user_id OR $authorizer_user_id = '999'
        RETURN c, p
        """
        
        permission_result = session.run(permission_query, 
                                      comment_id=comment_id, 
                                      authorizer_user_id=authorizer_user_id)
        permission_record = permission_result.single()
        
        if not permission_record:
            print("Error: You don't have permission to authorize this comment")
            print("You must be the post owner or manager (ID 999)")
            return False
        
        # Authorize the comment
        authorize_query = """
        MATCH (c:Comment {idc: $comment_id})
        MATCH (authorizer_user:User {id: $authorizer_user_id})
        MERGE (authorizer_user)-[:AUTHORIZES]->(c)
        SET c.datea = datetime()
        RETURN c, authorizer_user
        """
        
        result = session.run(authorize_query, 
                           comment_id=comment_id,
                           authorizer_user_id=authorizer_user_id)
        record = result.single()
        
        if record:
            # Update the comments.txt file to add authorization
            update_comment_authorization(comment_id, authorizer_user_id)
            print(f"Comment '{comment_id}' authorized successfully by user {authorizer_user_id}")
            return True
        else:
            print("Error: Could not authorize comment")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 6. FILE UPDATE FUNCTIONS (se mantienen igual)
# =============================================================================
def update_user_in_file(user_id, new_name):
    """Update user in users.txt"""
    try:
        with open("users.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = []
        for line in lines:
            if user_id in line and line.strip() and not line.startswith('#'):
                parts = line.strip().split(',')
                if len(parts) >= 2 and parts[1] == user_id:
                    new_line = f"{new_name},{user_id}\n"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        with open("users.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
            
    except Exception as e:
        print(f"Error updating user in file: {e}")

def remove_user_from_file(user_id):
    """Remove user from users.txt"""
    try:
        with open("users.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = [line for line in lines if user_id not in line or line.startswith('#')]
        
        with open("users.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
            
    except Exception as e:
        print(f"Error removing user from file: {e}")

def update_post_in_file(post_id, new_content):
    """Update post in post.txt"""
    try:
        with open("post.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = []
        for line in lines:
            if post_id in line and line.strip() and not line.startswith('#'):
                parts = line.strip().split(',')
                if len(parts) >= 3 and parts[0] == post_id:
                    new_line = f"{post_id},{parts[1]},{new_content}\n"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        with open("post.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
            
    except Exception as e:
        print(f"Error updating post in file: {e}")

def remove_post_from_files(post_id):
    """Remove post from post.txt and associated comments from comments.txt"""
    try:
        # Remove from post.txt
        with open("post.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = [line for line in lines if post_id not in line or line.startswith('#')]
        with open("post.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
        
        # Remove associated comments from comments.txt
        with open("comments.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = [line for line in lines if post_id not in line or line.startswith('#')]
        with open("comments.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
            
    except Exception as e:
        print(f"Error removing post from files: {e}")

def update_comment_in_file(comment_id, new_content, new_like):
    """Update comment in comments.txt"""
    try:
        with open("comments.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = []
        for line in lines:
            if comment_id in line and line.strip() and not line.startswith('#'):
                parts = line.strip().split(',')
                if len(parts) >= 5 and parts[2] == comment_id:
                    like_str = "true" if new_like else "false"
                    new_line = f"{parts[0]},{parts[1]},{comment_id},{new_content},{like_str},{parts[5] if len(parts) > 5 else ''}\n"
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        with open("comments.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
            
    except Exception as e:
        print(f"Error updating comment in file: {e}")

def remove_comment_from_file(comment_id):
    """Remove comment from comments.txt"""
    try:
        with open("comments.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        new_lines = [line for line in lines if comment_id not in line or line.startswith('#')]
        
        with open("comments.txt", 'w', encoding='utf-8') as file:
            file.writelines(new_lines)
            
    except Exception as e:
        print(f"Error removing comment from file: {e}")

def update_comment_authorization(comment_id, authorizer_user_id):
    """
    Updates the comments.txt file to add authorization for a comment
    """
    try:
        # Read all lines from comments.txt
        with open("comments.txt", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Find and update the line with the comment
        updated = False
        new_lines = []
        for line in lines:
            if comment_id in line and line.strip() and not line.startswith('#'):
                # Check if authorization is already present
                parts = line.strip().split(',')
                if len(parts) >= 6 and not parts[5].strip():  # Empty authorizer field
                    parts[5] = authorizer_user_id
                    new_line = ','.join(parts) + '\n'
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # Write back to file if updated
        if updated:
            with open("comments.txt", 'w', encoding='utf-8') as file:
                file.writelines(new_lines)
            print(f"Authorization updated in comments.txt for comment {comment_id}")
        else:
            print(f"Comment {comment_id} not found in comments.txt or already authorized")
            
    except Exception as e:
        print(f"Error updating authorization in file: {e}")

# =============================================================================
# 7. INTERACTIVE MAIN MENU
# =============================================================================
def interactive_menu(session):
    """Main interactive menu"""
    # Create files if they don't exist
    create_files_if_not_exist()
    
    # Opción para limpiar archivos (preservando comentarios)
    clean_response = input("Clean existing files for proper formatting? (yes/no): ").strip().lower()
    if clean_response in ['yes', 'y', 'si', 'sí']:
        clean_files_preserve_comments()
    
    while True:
        print("\n" + "="*60)
        print("              MAIN MENU - NEO4J BLOG SYSTEM")
        print("="*60)
        print("1. Add User (Auto-ID)")
        print("2. Add Post (Auto-ID)") 
        print("3. Add Comment (Auto-ID)")
        print("4. Authorize Comment")
        print("5. View User Posts")
        print("6. View Post Comments")
        print("7. Edit User")
        print("8. Edit Post")
        print("9. Edit Comment")
        print("10. Delete User")
        print("11. Delete Post")
        print("12. Delete Comment")
        print("13. View generated files")
        print("14. Clean file formatting")
        print("15. Exit")
        print("="*60)
        
        option = input("Select an option (1-15): ").strip()
        
        if option == "1":
            insert_user_interactive(session)
        elif option == "2":
            insert_post_interactive(session)
        elif option == "3":
            insert_comment_interactive(session)
        elif option == "4":
            authorize_comment_interactive(session)
        elif option == "5":
            view_user_posts_interactive(session)
        elif option == "6":
            comments_from_user_post(session)
        elif option == "7":
            edit_user_interactive(session)
        elif option == "8":
            edit_post_interactive(session)
        elif option == "9":
            edit_comment_interactive(session)
        elif option == "10":
            delete_user_interactive(session)
        elif option == "11":
            delete_post_interactive(session)
        elif option == "12":
            delete_comment_interactive(session)
        elif option == "13":
            print("\n=== GENERATED FILES ===")
            files = ["users.txt", "post.txt", "comments.txt"]
            for filename in files:
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                    # Count non-empty, non-comment lines
                    data_lines = [line for line in lines if line.strip() and not line.startswith('#')]
                    print(f"{filename}: {len(data_lines)} records")
                else:
                    print(f"{filename}: Does not exist")
        elif option == "14":
            clean_files_preserve_comments()
        elif option == "15":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select 1-15")  # ← ESTA LÍNEA FALTABA

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    try:
        with driver.session() as session:
            print("🚀 Initializing Blog Neo4j Session...")
            interactive_menu(session)
    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        driver.close()
        print("👋 Finalizing Session")