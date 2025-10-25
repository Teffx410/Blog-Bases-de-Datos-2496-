import neo4j
from dotenv import load_dotenv
import os
from datetime import datetime

# Connection configuration
load_dotenv()
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

try:
    driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
    print("Connected to Neo4j successfully!")
except Exception as e:
    print(f"Connection error: {e}")
    exit(1)

# =============================================================================
# FUNCTIONS TO SAVE TO .txt FILES
# =============================================================================
def save_to_file(filename, line):
    """Saves a new line to the corresponding file"""
    try:
        with open(filename, 'a', encoding='utf-8') as file:
            file.write(line + '\n')  # This should create a new line
        print(f"Data saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving to file: {e}")
        return False

# =============================================================================
# AUTHORIZATION FUNCTION
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
# 1. FUNCTION TO INSERT USER
# =============================================================================
def insert_user_interactive(session):
    print("\n=== ADD NEW USER ===")
    
    try:
        user_id = input("User ID: ").strip()
        name = input("User name: ").strip()
        
        if not user_id or not name:
            print("Error: ID and name are required")
            return False
            
        query = """
        MERGE (u:User {id: $user_id})
        SET u.name = $name
        RETURN u
        """
        
        result = session.run(query, user_id=user_id, name=name)
        record = result.single()
        
        if record:
            # Save to users.txt file - ensure new line
            line = f"{name},{user_id}"
            if save_to_file("users.txt", line):
                print(f"User '{name}' (ID: {user_id}) created successfully and saved to file")
            return True
        else:
            print("Error creating user")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 2. FUNCTION TO INSERT POST
# =============================================================================
def insert_post_interactive(session):
    print("\n=== ADD NEW POST ===")
    
    try:
        post_id = input("Post ID: ").strip()
        user_id = input("Author user ID: ").strip()
        content = input("Post content: ").strip()
        
        if not post_id or not user_id or not content:
            print("Error: All fields are required")
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
            # Save to posts.txt file - ensure new line
            line = f"{post_id},{user_id},{content}"
            if save_to_file("post.txt", line):
                print(f"Post '{post_id}' created successfully for user {user_id} and saved to file")
            return True
        else:
            print(f"Error: Could not create post. Verify that user {user_id} exists")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 3. FUNCTION TO INSERT COMMENT
# =============================================================================
def insert_comment_interactive(session):
    print("\n=== ADD NEW COMMENT ===")
    
    try:
        comment_id = input("Comment ID: ").strip()
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
        
        if not all([comment_id, post_id, author_user_id, content]):
            print("Error: All fields except authorization are required")
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
            # Save to comments.txt file - ensure new line
            if authorizer_user_id:
                line = f"{post_id},{author_user_id},{comment_id},{content},{like_str},{authorizer_user_id}"
            else:
                line = f"{post_id},{author_user_id},{comment_id},{content},{like_str},"
            
            if save_to_file("comments.txt", line):
                if authorizer_user_id:
                    print(f"Comment '{comment_id}' created, authorized and saved to file")
                else:
                    print(f"Comment '{comment_id}' created (pending authorization) and saved to file")
            return True
        else:
            print("Error: Could not create comment. Verify that post and user exist")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# =============================================================================
# 4. FUNCTION TO CREATE FILES IF THEY DON'T EXIST
# =============================================================================
def create_files_if_not_exist():
    """Creates .txt files if they don't exist"""
    files = {
        "users.txt": "# Format: name,id\n",
        "post.txt": "# Format: post_id,user_id,content\n", 
        "comments.txt": "# Format: post_id,author_user_id,comment_id,content,like,authorizer_user_id\n"
    }
    
    for filename, header in files.items():
        if not os.path.exists(filename):
            try:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(header)
                print(f"File {filename} created successfully")
            except Exception as e:
                print(f"Error creating {filename}: {e}")

# =============================================================================
# 5. INTERACTIVE MAIN MENU
# =============================================================================
def interactive_menu(session):
    """Main interactive menu"""
    # Create files if they don't exist
    create_files_if_not_exist()
    
    while True:
        print("\n" + "="*50)
        print("        MAIN MENU - NEO4J")
        print("="*50)
        print("1. Add User")
        print("2. Add Post") 
        print("3. Add Comment")
        print("4. Authorize Comment")
        print("5. View generated files")
        print("6. Exit")
        print("="*50)
        
        option = input("Select an option (1-6): ").strip()
        
        if option == "1":
            insert_user_interactive(session)
        elif option == "2":
            insert_post_interactive(session)
        elif option == "3":
            insert_comment_interactive(session)
        elif option == "4":
            authorize_comment_interactive(session)
        elif option == "5":
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
        elif option == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select 1-6")

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    with driver.session() as session:
        interactive_menu(session)
    driver.close()