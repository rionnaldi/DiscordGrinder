import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import re
import os
from urllib.parse import urljoin
from colorama import Fore, Style, init
import json
import unicodedata
import google.generativeai as genai
import asyncio

# Initialize colorama for colored output
init(autoreset=True)

class KnowledgeRetriever:
    """
    Handles retrieval, processing, and chunking of technical content for RAG (Retrieval-Augmented Generation).
    Scrapes technical content from websites and prepares it for storage and retrieval.
    """
    
    def __init__(self, api_key: str, base_urls: List[str] = None):
        """
        Initialize the knowledge retriever.
        
        Args:
            api_key: Google Gemini API key for generating embeddings
            base_urls: List of base URLs to scrape for technical content
        """        
        self.base_urls = base_urls or [""]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.api_key = api_key
        genai.configure(api_key=api_key)
        print(f"{Fore.GREEN}[KNOWLEDGE] Initialized Knowledge Retriever with {len(self.base_urls)} source URLs")
    async def scrape_technical_content(self) -> List[Dict]:
        """
        Scrape technical content from configured URLs using aiohttp.
        
        Returns:
            List of dictionaries containing chunks of technical content
        """
        all_content = []
        # Create a single session to be reused for all requests
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for url in self.base_urls:
                try:
                    print(f"{Fore.CYAN}[KNOWLEDGE] Scraping content from: {url}")
                    # Fetch page content asynchronously
                    async with session.get(url) as response:
                        response.raise_for_status()
                        html_text = await response.text(encoding='utf-8')

                    # Parse HTML
                    soup = BeautifulSoup(html_text, 'html.parser')
                    content_elements = self._extract_content_elements(soup, url)
                    
                    if not content_elements:
                        print(f"{Fore.YELLOW}[KNOWLEDGE] No content found for: {url}")
                        continue
                    
                    # Process and chunk the content
                    chunks = await self._chunk_content(content_elements, url)
                    all_content.extend(chunks)
                    
                    # Be respectful with scraping - add async delay
                    if len(self.base_urls) > 1:
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"{Fore.RED}[KNOWLEDGE] Error scraping {url}: {str(e)}")

        print(f"{Fore.GREEN}[KNOWLEDGE] Scraped {len(all_content)} content chunks from {len(self.base_urls)} URLs")
        return all_content
    
    def _extract_content_elements(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """
        Extract content elements from BeautifulSoup object.
        Enhanced to handle a wide variety of website structures.
        
        Args:
            soup: BeautifulSoup object of the page
            url: Source URL
            
        Returns:
            List of dictionaries with content elements
        """
        elements = []
        
        try:
            print(f"{Fore.CYAN}[KNOWLEDGE] Extracting content from URL: {url}")
            
            # First try - target specific content areas with common selectors
            article = None
            
            # Expanded list of content selectors for common website structures
            potential_containers = [
                # Standard article containers
                'article', 'main', 'section', 
                
                # Common content wrappers
                'div.post-content', 'div.entry-content', 'div.content', 'div.post', 'div.article', 
                'div.page-content', 'div.blog-post', 'div.blog-content', 'div.markdown-content',
                
                # Content IDs
                '#content', '#main-content', '#post-content', '#article-content', '#page-content',
                
                # Modern website structures (single page apps, etc.)
                'div.container', 'div.wrapper', 'div.inner', 'div.main',
                
                # Specific to documentation sites
                'div.documentation', 'div.docs', 'div.doc-content',
                
                # Specific to corporate/product sites
                'div.product-description', 'div.terms', 'div.terms-content', 'div.legal',
                
                # Special sections
                'div.hero-text', 'div.text-content', 'div.description'
            ]
            
            # Try to find a container using the expanded selectors
            for selector in potential_containers:
                if '.' in selector or '#' in selector:
                    # CSS selector format
                    try:
                        found = soup.select_one(selector)
                        if found and found.get_text(strip=True):
                            article = found
                            print(f"{Fore.GREEN}[KNOWLEDGE] Found content using selector: {selector}")
                            break
                    except Exception:
                        continue
                else:
                    # Direct tag name
                    found = soup.find(selector)
                    if found and found.get_text(strip=True):
                        article = found
                        print(f"{Fore.GREEN}[KNOWLEDGE] Found content using tag: {selector}")
                        break
            
            # If still not found, try searching for text-dense regions
            if not article:
                print(f"{Fore.YELLOW}[KNOWLEDGE] No standard content containers found, looking for text-dense regions")
                
                # Look for divs with substantial text
                text_containers = []
                
                for div in soup.find_all('div'):
                    # Skip tiny divs and obvious navigation/header/footer elements
                    if 'nav' in div.get('class', []) or 'header' in div.get('class', []) or 'footer' in div.get('class', []):
                        continue
                        
                    text = div.get_text(strip=True)
                    if len(text) > 100:  # Only divs with substantial text
                        text_containers.append((div, len(text)))
                
                # Sort by text length to find the most content-rich divs
                text_containers.sort(key=lambda x: x[1], reverse=True)
                
                if text_containers:
                    # Use the div with the most text
                    article = text_containers[0][0]
                    print(f"{Fore.GREEN}[KNOWLEDGE] Found text-dense region with {text_containers[0][1]} characters")
                else:
                    # Last resort - use the body if nothing else works
                    article = soup.find('body')
                    print(f"{Fore.YELLOW}[KNOWLEDGE] Using body as fallback")
            
            # If an article container was found, extract its elements
            if article:
                # Expanded list of element types to look for
                element_types = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre', 'code', 
                                'ul', 'ol', 'img', 'a', 'b', 'strong', 'div', 'span', 
                                'blockquote', 'table', 'figure', 'figcaption']
                
                for element in article.find_all(element_types):
                    # Process headings
                    if element.name.startswith('h'):
                        text = element.get_text(strip=True)
                        text = self._clean_text(text)
                        
                        if not text:
                            continue
                            
                        # Check for any links inside the heading
                        links = self._extract_links_from_element(element, url)
                        
                        elements.append({
                            'type': element.name,
                            'text': text,
                            'level': int(element.name[1]),
                            'links': links if links else []
                        })
                    
                    # Process paragraphs, spans, and div elements with text
                    elif element.name in ['p', 'div', 'span', 'blockquote']:
                        # Skip if this element is too large or likely a container
                        if element.name == 'div':
                            # More permissive rules for divs - allow more nested elements
                            if len(element.find_all(['div'])) > 3:
                                continue
                                
                            # Skip divs that look like layout containers
                            skip_classes = ['container', 'row', 'wrapper', 'header', 'footer', 'navbar']
                            if any(cls in element.get('class', []) for cls in skip_classes):
                                continue
                        
                        # Skip empty elements or just whitespace
                        text = element.get_text(strip=True)
                        if not text:
                            continue
                            
                        text = self._clean_text(text)
                        
                        # Extract any links from the paragraph
                        links = self._extract_links_from_element(element, url)
                        
                        # Extract any images from the paragraph
                        images = self._extract_images_from_element(element, url)
                        
                        if text:
                            paragraph_element = {
                                'type': 'p',
                                'text': text
                            }
                            
                            # Add links if found
                            if links:
                                paragraph_element['links'] = links
                                
                            # Add images if found
                            if images:
                                paragraph_element['images'] = images
                                
                            elements.append(paragraph_element)
                    
                    # Process code blocks
                    elif element.name in ['pre', 'code']:
                        text = element.get_text(strip=True)
                        text = self._clean_text(text)
                        
                        if text:
                            elements.append({
                                'type': 'code',
                                'text': text
                            })
                    
                    # Process lists
                    elif element.name in ['ul', 'ol']:
                        list_items = []
                        
                        # Get all list items, even from nested lists
                        for li in element.find_all('li'):
                            # Check if this li belongs to a nested list
                            parents = [p.name for p in li.parents]
                            if element.name in parents and parents.index(element.name) > 0:
                                # Skip items from nested lists
                                continue
                                
                            item_text = li.get_text(strip=True)
                            item_text = self._clean_text(item_text)
                            
                            if item_text:
                                list_items.append(item_text)
                        
                        if list_items:
                            elements.append({
                                'type': element.name,  # 'ul' or 'ol'
                                'items': list_items
                            })
                    
                    # Process images directly
                    elif element.name == 'img' and element.get('src'):
                        img_src = element.get('src')
                        img_alt = element.get('alt', '')
                        
                        # Convert relative URLs to absolute
                        if not img_src.startswith(('http://', 'https://')):
                            img_src = urljoin(url, img_src)
                        
                        elements.append({
                            'type': 'img',
                            'src': img_src,
                            'alt': img_alt
                        })
                        
                    # Process tables
                    elif element.name == 'table':
                        # Extract table data as text
                        table_text = "Table: " + element.get_text(strip=True)
                        table_text = self._clean_text(table_text)
                        
                        if table_text and len(table_text) > 10:  # Ensure it's not just "Table:"
                            elements.append({
                                'type': 'p',  # Treat as paragraph for simplicity
                                'text': table_text
                            })
            
            # Fallback: If no elements were found or they're all empty, extract everything visible
            if not elements:
                print(f"{Fore.YELLOW}[KNOWLEDGE] No structured elements found, using fallback extraction")
                
                # Extract text from all visible elements, grouped by section
                fallback_elements = self._extract_visible_text_as_sections(soup, url)
                if fallback_elements:
                    elements.extend(fallback_elements)
                    print(f"{Fore.GREEN}[KNOWLEDGE] Extracted {len(fallback_elements)} elements using fallback method")
            
            # Final fallback: Extract all visible text as a single chunk
            if not elements:
                print(f"{Fore.YELLOW}[KNOWLEDGE] Still no elements found, using raw text extraction")
                
                # Extract all visible text
                all_text = soup.get_text(separator=' ', strip=True)
                all_text = self._clean_text(all_text)
                
                if all_text:
                    elements.append({
                        'type': 'p',
                        'text': all_text
                    })
                    print(f"{Fore.GREEN}[KNOWLEDGE] Extracted {len(all_text)} characters of raw text")
            
            # Print stats about extraction
            text_length = sum(len(e.get('text', '')) for e in elements if 'text' in e)
            print(f"{Fore.GREEN}[KNOWLEDGE] Extracted {len(elements)} elements with total text length of {text_length} characters")
            
            return elements
            
        except Exception as e:
            print(f"{Fore.RED}[KNOWLEDGE] Error extracting content elements: {str(e)}")
            return []
    
    async def _chunk_content(self, content_elements: List[Dict], url: str) -> List[Dict]:
        """
        Process and chunk content elements into digestible pieces.
        
        Args:
            content_elements: List of content element dictionaries
            url: Source URL
            
        Returns:
            List of chunked content dictionaries with embeddings
        """
        chunks = []
        current_chunk = []
        current_chunk_text = ""
        chunk_id = 1
        
        for element in content_elements:
            element_text = ""
            
            # Extract text based on element type
            if element['type'].startswith('h'):
                element_text = element['text']
            elif element['type'] == 'p':
                element_text = element['text']
            elif element['type'] == 'code':
                element_text = f"Code: {element['text']}"
            elif element['type'] in ['ul', 'ol']:
                element_text = "\n".join([f"- {item}" for item in element['items']])            
            elif element['type'] == 'img':
                element_text = f"Image: {element['alt']}" if element['alt'] else "Image"
            
            # Skip empty elements
            if not element_text or element_text.strip() == "":
                continue
              # Check if adding this element would exceed chunk size
            if len(current_chunk_text) + len(element_text) > 1000 and current_chunk:
                # Create a chunk from accumulated elements
                chunk_text = " ".join([self._element_to_text(e) for e in current_chunk])
                
                # Skip empty chunks
                if not chunk_text or chunk_text.strip() == "":
                    print(f"{Fore.YELLOW}[KNOWLEDGE] Skipping empty chunk from {url}")
                    current_chunk = []
                    current_chunk_text = ""
                    continue
                
                # Generate embedding for the chunk
                embedding = await self._generate_embedding(chunk_text)
                
                chunks.append({
                    'chunk_id': f"{url.split('/')[-1]}_{chunk_id}",
                    'source_url': url,
                    'content': chunk_text,
                    'elements': current_chunk.copy(),
                    'embedding': embedding
                })
                
                chunk_id += 1
                current_chunk = []
                current_chunk_text = ""
            
            # Add current element to chunk
            current_chunk.append(element)
            current_chunk_text += element_text + " "
          # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join([self._element_to_text(e) for e in current_chunk])
            
            # Skip empty chunks
            if not chunk_text or chunk_text.strip() == "":
                print(f"{Fore.YELLOW}[KNOWLEDGE] Skipping empty chunk from {url}")
                return chunks
                
            # Generate embedding for the chunk
            embedding = await self._generate_embedding(chunk_text)
            chunks.append({
                'chunk_id': f"{url.split('/')[-1]}_{chunk_id}",
                'source_url': url,
                'content': chunk_text,
                'elements': current_chunk,
                'embedding': embedding
            })
        return chunks
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the text using Gemini API.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            # Check if text is empty
            if not text or text.strip() == "":
                print(f"{Fore.YELLOW}[KNOWLEDGE] Cannot generate embedding for empty text, returning empty vector")
                return []
                
            # Clean and normalize the text
            clean_text = self._clean_text(text) if hasattr(self, '_clean_text') else text
            
            # Check again after cleaning
            if not clean_text or clean_text.strip() == "":
                print(f"{Fore.YELLOW}[KNOWLEDGE] Text became empty after cleaning, returning empty vector")
                return []
            
            # Use Google's generative model for embeddings via asyncio.to_thread
            result = await asyncio.to_thread(
                genai.embed_content,
                model="models/text-embedding-004",
                content=clean_text,
                task_type="RETRIEVAL_DOCUMENT"
            )
            
            # Extract and return the embedding values
            if result and hasattr(result, 'embedding'):
                return result.embedding
            return []
                
        except Exception as e:
            print(f"{Fore.RED}[KNOWLEDGE] Error generating embedding: {str(e)}")
            return []
    
    def _element_to_text(self, element: Dict) -> str:
        """
        Convert an element dictionary to plain text.
        
        Args:
            element: Element dictionary
            
        Returns:
            Plain text representation
        """
        element_type = element.get('type', 'text')
        text = element.get('text', '')
        
        if element_type == 'heading':
            return f"{text}\n"
        else:
            return f"{text}\n\n"
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for better embedding generation.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
          # Normalize unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Remove special characters that don't add semantic meaning
        text = re.sub(r'[^\w\s.,!?;:()\[\]{}-]', '', text)
        
        return text.strip()
    
    def _extract_visible_text_as_sections(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """
        Extract all visible text content from the page, grouped into logical sections.
        Used as a fallback when standard content selectors fail.
        
        Args:
            soup: BeautifulSoup object of the page
            url: Source URL
            
        Returns:
            List of dictionaries with extracted text
        """
        elements = []
        
        try:
            # Look for all potential content sections by grouping visible elements
            for heading in soup.find_all(['h1', 'h2', 'h3']):
                # Extract the heading text
                heading_text = heading.get_text(strip=True)
                if not heading_text:
                    continue
                
                heading_text = self._clean_text(heading_text)
                
                # Add the heading element
                elements.append({
                    'type': heading.name,
                    'text': heading_text,
                    'level': int(heading.name[1]),
                    'links': self._extract_links_from_element(heading, url) or []
                })
                
                # Find all sibling elements until the next heading of same or higher level
                current = heading.next_sibling
                section_text = ""
                
                while current and not (
                    current.name in ['h1', 'h2', 'h3'] and 
                    int(current.name[1]) <= int(heading.name[1]) if current.name and current.name[0] == 'h' and len(current.name) > 1 else False
                ):
                    # Only process elements that have visible text
                    if current.name in ['p', 'div', 'span', 'li', 'blockquote'] and current.get_text(strip=True):
                        current_text = current.get_text(strip=True)
                        if current_text:
                            section_text += current_text + " "
                    
                    # Move to next element
                    current = current.next_sibling
                
                # Add the section text if any was found
                if section_text:
                    section_text = self._clean_text(section_text)
                    elements.append({
                        'type': 'p',
                        'text': section_text
                    })
            
            # If we still don't have any elements, look for large text blocks
            if not elements:
                # Find all paragraphs, divs with text, and list items
                text_elements = []
                
                for tag in soup.find_all(['p', 'div', 'li']):
                    text = tag.get_text(strip=True)
                    if len(text) > 50:  # Only consider substantial text blocks
                        text_elements.append({
                            'type': 'p',
                            'text': self._clean_text(text)
                        })
                
                # Sort by text length and take the top elements
                text_elements.sort(key=lambda x: len(x.get('text', '')), reverse=True)
                elements.extend(text_elements[:10])  # Take the top 10 text blocks
            
            return elements
            
        except Exception as e:
            print(f"{Fore.RED}[KNOWLEDGE] Error in fallback extraction: {str(e)}")
            return []
    
    def _extract_links_from_element(self, element, base_url: str) -> List[Dict]:
        """
        Extract links from an element.
        
        Args:
            element: BeautifulSoup element
            base_url: Base URL for resolving relative links
            
        Returns:
            List of link dictionaries
        """
        links = []
        
        for a_tag in element.find_all('a', href=True):
            href = a_tag.get('href')
            text = a_tag.get_text(strip=True)
            
            # Skip empty links
            if not href or href.startswith('#'):
                continue
                
            # Convert relative URLs to absolute
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            
            links.append({
                'url': href,
                'text': text if text else href
            })
        
        return links
    
    def _extract_images_from_element(self, element, base_url: str) -> List[Dict]:
        """
        Extract images from an element.
        
        Args:
            element: BeautifulSoup element
            base_url: Base URL for resolving relative links
            
        Returns:
            List of image dictionaries
        """
        images = []
        
        for img_tag in element.find_all('img', src=True):
            src = img_tag.get('src')
            alt = img_tag.get('alt', '')
            
            # Convert relative URLs to absolute
            if not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            
            images.append({
                'src': src,
                'alt': alt
            })
        
        return images
    
    async def populate_knowledge_base(self, mongo_manager) -> int:
        """
        Scrape content and populate the knowledge base.
        
        Args:
            mongo_manager: MongoManager instance
            
        Returns:
            Number of chunks stored
        """
        try:
            print(f"{Fore.CYAN}[KNOWLEDGE] Populating knowledge base...")
            
            # Scrape technical content
            content_chunks = await self.scrape_technical_content()
            
            if not content_chunks:
                print(f"{Fore.YELLOW}[KNOWLEDGE] No content chunks generated")
                return 0
            
            # Store chunks in MongoDB
            stored_count = await mongo_manager.store_technical_knowledge(content_chunks)
            
            print(f"{Fore.GREEN}[KNOWLEDGE] Knowledge base populated with {stored_count} new chunks")
            return stored_count
            
        except Exception as e:
            print(f"{Fore.RED}[KNOWLEDGE] Error populating knowledge base: {str(e)}")
            return 0
    
    def load_from_json(self, file_path: str) -> List[Dict]:
        """
        Load knowledge base from a JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List of content chunks
        """
        try:
            if not os.path.exists(file_path):
                print(f"{Fore.YELLOW}[KNOWLEDGE] JSON file not found: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"{Fore.GREEN}[KNOWLEDGE] Loaded {len(data)} chunks from JSON: {file_path}")
            return data
            
        except Exception as e:
            print(f"{Fore.RED}[KNOWLEDGE] Error loading from JSON: {str(e)}")
            return []
    
    def save_to_json(self, chunks: List[Dict], file_path: str) -> bool:
        """
        Save knowledge chunks to a JSON file.
        
        Args:
            chunks: List of content chunks
            file_path: Path to JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            
            print(f"{Fore.GREEN}[KNOWLEDGE] Saved {len(chunks)} chunks to JSON: {file_path}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}[KNOWLEDGE] Error saving to JSON: {str(e)}")
            return False
