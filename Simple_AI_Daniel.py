"""
Simplified Self-Learning AI System
A streamlined version with core learning capabilities and no external dependencies beyond basic Python libraries.
"""

import sqlite3
import json
import time
import random
from datetime import datetime

# Configuration
CONFIG = {
    "database_file": "simple_ai_brain.db",
    "max_memory_items": 500,
    "learning_rate": 0.05,
    "personality": {
        "curiosity": 0.7,
        "helpfulness": 0.8,
        "verbosity": 0.6
    }
}


class SimpleAI:
    def __init__(self):
        self.db_file = CONFIG["database_file"]
        self.personality = CONFIG["personality"].copy()
        self.initialize_database()
        self.load_personality()
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Table for storing interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                feedback TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for storing learned knowledge
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for personality traits
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personality (
                trait TEXT PRIMARY KEY,
                value REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_personality(self):
        """Load personality from database or initialize with defaults"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        for trait, value in self.personality.items():
            cursor.execute('SELECT value FROM personality WHERE trait = ?', (trait,))
            result = cursor.fetchone()
            
            if result:
                self.personality[trait] = result[0]
            else:
                cursor.execute('INSERT INTO personality (trait, value) VALUES (?, ?)', 
                             (trait, value))
        
        conn.commit()
        conn.close()
    
    def save_personality(self):
        """Save current personality to database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        for trait, value in self.personality.items():
            cursor.execute('UPDATE personality SET value = ? WHERE trait = ?', 
                         (value, trait))
        
        conn.commit()
        conn.close()
    
    def store_interaction(self, query, response, feedback=None):
        """Store an interaction in the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interactions (query, response, feedback)
            VALUES (?, ?, ?)
        ''', (query, response, feedback))
        
        conn.commit()
        conn.close()
    
    def extract_keywords(self, text):
        """Extract important keywords from text"""
        # Remove common words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'can',
                     'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
                     'into', 'through', 'during', 'before', 'after', 'above', 'below',
                     'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
                     'under', 'again', 'further', 'then', 'once', 'here', 'there',
                     'when', 'where', 'why', 'how', 'all', 'both', 'each', 'few',
                     'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                     'only', 'own', 'same', 'so', 'than', 'too', 'very', 'what'}
        
        words = text.lower().split()
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        return list(set(keywords))
    
    def find_similar_queries(self, query, limit=3):
        """Find similar past queries"""
        keywords = self.extract_keywords(query)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT query, response, feedback 
            FROM interactions 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        
        past_interactions = cursor.fetchall()
        conn.close()
        
        # Score each past interaction by keyword overlap
        scored = []
        for past_query, past_response, feedback in past_interactions:
            past_keywords = self.extract_keywords(past_query)
            overlap = len(set(keywords) & set(past_keywords))
            if overlap > 0:
                scored.append((past_query, past_response, feedback, overlap))
        
        # Sort by overlap score
        scored.sort(key=lambda x: x[3], reverse=True)
        return scored[:limit]
    
    def store_knowledge(self, topic, content):
        """Store learned knowledge about a topic"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO knowledge (topic, content, confidence)
                VALUES (?, ?, 0.5)
                ON CONFLICT(topic) DO UPDATE SET
                    content = content || ' | ' || excluded.content,
                    confidence = MIN(confidence + 0.1, 1.0),
                    timestamp = CURRENT_TIMESTAMP
            ''', (topic, content))
            
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error storing knowledge: {e}")
        finally:
            conn.close()
    
    def retrieve_knowledge(self, keywords):
        """Retrieve relevant knowledge based on keywords"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT topic, content, confidence FROM knowledge')
        all_knowledge = cursor.fetchall()
        conn.close()
        
        # Find relevant knowledge
        relevant = []
        for topic, content, confidence in all_knowledge:
            topic_keywords = self.extract_keywords(topic)
            overlap = len(set(keywords) & set(topic_keywords))
            if overlap > 0:
                relevant.append((topic, content, confidence, overlap))
        
        relevant.sort(key=lambda x: (x[3], x[2]), reverse=True)
        return relevant[:3]
    
    def generate_response(self, query):
        """Generate a response to the query"""
        keywords = self.extract_keywords(query)
        
        # Check for similar past queries
        similar = self.find_similar_queries(query)
        
        # Retrieve relevant knowledge
        knowledge = self.retrieve_knowledge(keywords)
        
        # Build response
        response_parts = []
        
        # Use knowledge base
        if knowledge:
            response_parts.append("Based on what I know:")
            for topic, content, confidence, _ in knowledge[:2]:
                response_parts.append(f"- {topic}: {content[:200]}")
        
        # Use similar past interactions
        if similar and self.personality["curiosity"] > 0.5:
            response_parts.append("\nI recall similar questions:")
            for past_query, past_response, feedback, _ in similar[:1]:
                if feedback == "positive":
                    response_parts.append(f"Previously: {past_response[:150]}")
        
        # Add curiosity-based follow-up
        if self.personality["curiosity"] > 0.6 and random.random() < self.personality["curiosity"]:
            follow_ups = self.generate_follow_up_questions(query)
            if follow_ups:
                response_parts.append("\n" + follow_ups[0])
        
        # If no specific knowledge, provide general response
        if not response_parts:
            response_parts.append(
                "I don't have specific information about this yet, but I'm learning! "
                "Could you provide more details or context?"
            )
        
        return "\n".join(response_parts)
    
    def generate_follow_up_questions(self, query):
        """Generate follow-up questions based on curiosity"""
        templates = [
            "Would you like me to elaborate on any aspect?",
            "Is there a specific part you'd like to explore more?",
            "Can you tell me more about your specific use case?",
            "What aspect of this interests you most?"
        ]
        
        num_questions = 1 if self.personality["curiosity"] < 0.7 else 2
        return random.sample(templates, min(num_questions, len(templates)))
    
    def learn_from_feedback(self, query, response, feedback):
        """Adjust personality and knowledge based on feedback"""
        learning_rate = CONFIG["learning_rate"]
        
        if feedback == "positive":
            # Reinforce current approach
            if "?" in response:
                self.personality["curiosity"] = min(1.0, 
                    self.personality["curiosity"] + learning_rate)
            
            if len(response.split()) > 50:
                self.personality["verbosity"] = min(1.0,
                    self.personality["verbosity"] + learning_rate)
            
            # Store successful patterns as knowledge
            keywords = self.extract_keywords(query)
            for keyword in keywords[:3]:
                self.store_knowledge(keyword, response[:300])
        
        elif feedback == "negative":
            # Adjust personality
            self.personality["curiosity"] = max(0.3,
                self.personality["curiosity"] - learning_rate)
            self.personality["verbosity"] = max(0.3,
                self.personality["verbosity"] - learning_rate)
        
        # Save updated personality
        self.save_personality()
    
    def prune_old_data(self):
        """Remove old data to prevent database bloat"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Keep only recent interactions
        cursor.execute('''
            DELETE FROM interactions 
            WHERE id NOT IN (
                SELECT id FROM interactions 
                ORDER BY timestamp DESC 
                LIMIT ?
            )
        ''', (CONFIG["max_memory_items"],))
        
        conn.commit()
        conn.close()
    
    def chat(self, query):
        """Main chat interface"""
        # Generate response
        response = self.generate_response(query)
        
        # Store interaction
        self.store_interaction(query, response)
        
        # Periodically prune old data
        if random.random() < 0.1:
            self.prune_old_data()
        
        return response
    
    def get_stats(self):
        """Get statistics about the AI's learning"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM interactions')
        interaction_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM knowledge')
        knowledge_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM interactions 
            WHERE feedback = "positive"
        ''')
        positive_feedback = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_interactions": interaction_count,
            "knowledge_items": knowledge_count,
            "positive_feedback": positive_feedback,
            "personality": self.personality
        }


def main():
    """Main interaction loop"""
    print("=" * 50)
    print("Simple Self-Learning AI System")
    print("=" * 50)
    print("\nInitializing...")
    
    ai = SimpleAI()
    
    print("System ready!")
    print("\nCommands:")
    print("  - Type your question to chat")
    print("  - Type 'stats' to see learning statistics")
    print("  - Type 'exit' to quit")
    print("=" * 50)
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("\nGoodbye! I'll remember our conversation.")
                break
            
            if user_input.lower() == 'stats':
                stats = ai.get_stats()
                print("\n--- Learning Statistics ---")
                print(f"Total interactions: {stats['total_interactions']}")
                print(f"Knowledge items: {stats['knowledge_items']}")
                print(f"Positive feedback: {stats['positive_feedback']}")
                print("\nPersonality:")
                for trait, value in stats['personality'].items():
                    print(f"  {trait.capitalize()}: {value:.2f}")
                continue
            
            # Generate response
            response = ai.chat(user_input)
            print(f"\nAI: {response}")
            
            # Get feedback
            feedback_input = input("\nWas this helpful? (y/n/skip): ").lower()
            
            if feedback_input == 'y':
                ai.learn_from_feedback(user_input, response, "positive")
                print("Thanks! I'll remember that.")
            elif feedback_input == 'n':
                ai.learn_from_feedback(user_input, response, "negative")
                print("I'll try to improve.")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! I'll remember our conversation.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Let's try again...")


if __name__ == "__main__":
    main()