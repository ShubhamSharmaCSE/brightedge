"""
Test the crawler with the provided URLs.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, List


class CrawlerTester:
    """Test the crawler with the provided URLs."""
    
    def __init__(self):
        self.test_urls = [
            "http://www.amazon.com/Cuisinart-CPT-122-Compact-2-Slice-Toaster/dp/B009GQ034C/ref=sr_1_1?s=kitchen&ie=UTF8&qid=1431620315&sr=1-1&keywords=toaster",
            "http://blog.rei.com/camp/how-to-introduce-your-indoorsy-friend-to-the-outdoors/",
            "http://www.cnn.com/2013/06/10/politics/edward-snowden-profile/"
        ]
        self.base_url = "http://localhost:8000"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def test_single_crawl(self, url: str) -> Dict[str, Any]:
        """Test crawling a single URL."""
        print(f"\n🔍 Testing crawl of: {url}")
        
        try:
            # Submit crawl request
            response = await self.client.post(
                f"{self.base_url}/api/v1/crawl",
                json={"url": url}
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to submit crawl request: {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": f"HTTP {response.status_code}"}
            
            crawl_data = response.json()
            crawl_id = crawl_data["crawl_id"]
            print(f"✅ Crawl submitted with ID: {crawl_id}")
            
            # Wait for completion and get results
            max_attempts = 30
            for attempt in range(max_attempts):
                await asyncio.sleep(2)  # Wait 2 seconds between checks
                
                result_response = await self.client.get(
                    f"{self.base_url}/api/v1/results/{crawl_id}"
                )
                
                if result_response.status_code == 200:
                    result_data = result_response.json()
                    status = result_data.get("status")
                    
                    if status == "completed":
                        print(f"✅ Crawl completed successfully")
                        return result_data
                    elif status == "failed":
                        print(f"❌ Crawl failed: {result_data.get('error_message', 'Unknown error')}")
                        return result_data
                    else:
                        print(f"⏳ Crawl status: {status} (attempt {attempt + 1}/{max_attempts})")
                else:
                    print(f"❌ Failed to get results: {result_response.status_code}")
            
            print(f"⏰ Crawl timed out after {max_attempts} attempts")
            return {"error": "timeout"}
            
        except Exception as e:
            print(f"❌ Error during crawl: {str(e)}")
            return {"error": str(e)}
    
    async def test_batch_crawl(self) -> Dict[str, Any]:
        """Test batch crawling of all URLs."""
        print(f"\n🔍 Testing batch crawl of {len(self.test_urls)} URLs")
        
        try:
            # Submit batch crawl request
            response = await self.client.post(
                f"{self.base_url}/api/v1/crawl/batch",
                json={"urls": self.test_urls}
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to submit batch crawl request: {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": f"HTTP {response.status_code}"}
            
            batch_data = response.json()
            batch_id = batch_data["batch_id"]
            print(f"✅ Batch crawl submitted with ID: {batch_id}")
            
            # Wait for completion
            max_attempts = 60  # More time for batch processing
            for attempt in range(max_attempts):
                await asyncio.sleep(3)  # Wait 3 seconds between checks
                
                # Check individual results
                completed_count = 0
                failed_count = 0
                
                for result in batch_data["results"]:
                    crawl_id = result["crawl_id"]
                    
                    result_response = await self.client.get(
                        f"{self.base_url}/api/v1/results/{crawl_id}"
                    )
                    
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        status = result_data.get("status")
                        
                        if status == "completed":
                            completed_count += 1
                        elif status == "failed":
                            failed_count += 1
                
                total_processed = completed_count + failed_count
                
                if total_processed == len(self.test_urls):
                    print(f"✅ Batch crawl completed: {completed_count} successful, {failed_count} failed")
                    return {
                        "batch_id": batch_id,
                        "completed": completed_count,
                        "failed": failed_count,
                        "total": len(self.test_urls)
                    }
                else:
                    print(f"⏳ Batch progress: {total_processed}/{len(self.test_urls)} processed (attempt {attempt + 1}/{max_attempts})")
            
            print(f"⏰ Batch crawl timed out after {max_attempts} attempts")
            return {"error": "timeout"}
            
        except Exception as e:
            print(f"❌ Error during batch crawl: {str(e)}")
            return {"error": str(e)}
    
    async def test_health_check(self) -> bool:
        """Test health check endpoint."""
        print(f"\n🔍 Testing health check")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed: {health_data.get('status')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False
    
    def analyze_results(self, results: List[Dict[str, Any]]):
        """Analyze and display crawl results."""
        print(f"\n📊 Analyzing Results")
        print("=" * 50)
        
        for i, result in enumerate(results, 1):
            if "error" in result:
                print(f"\n{i}. ❌ FAILED")
                print(f"   Error: {result['error']}")
                continue
            
            metadata = result.get("metadata", {})
            url = result.get("url", "Unknown")
            
            print(f"\n{i}. ✅ SUCCESS")
            print(f"   URL: {url}")
            print(f"   Title: {metadata.get('title', 'N/A')}")
            print(f"   Description: {metadata.get('description', 'N/A')[:100]}...")
            print(f"   Keywords: {len(metadata.get('keywords', []))} found")
            print(f"   Word Count: {metadata.get('word_count', 0)}")
            print(f"   Images: {len(metadata.get('images', []))}")
            print(f"   Links: {len(metadata.get('links', []))}")
            print(f"   Topics: {len(metadata.get('topics', []))}")
            
            # Show topics
            topics = metadata.get("topics", [])
            if topics:
                print(f"   Topic Classifications:")
                for topic in topics[:3]:  # Show top 3 topics
                    print(f"     - {topic.get('topic', 'Unknown')}: {topic.get('confidence', 0):.2f}")
            
            print(f"   Response Time: {metadata.get('response_time_ms', 0)}ms")
            print(f"   Status Code: {metadata.get('status_code', 'Unknown')}")
    
    async def run_tests(self):
        """Run all tests."""
        print("🚀 Starting BrightEdge Crawler Tests")
        print("=" * 50)
        
        # Test health check first
        health_ok = await self.test_health_check()
        if not health_ok:
            print("❌ Health check failed, stopping tests")
            return
        
        # Test individual crawls
        individual_results = []
        for url in self.test_urls:
            result = await self.test_single_crawl(url)
            individual_results.append(result)
        
        # Test batch crawl
        batch_result = await self.test_batch_crawl()
        
        # Analyze results
        self.analyze_results(individual_results)
        
        # Summary
        print(f"\n📋 Test Summary")
        print("=" * 50)
        successful = sum(1 for r in individual_results if "error" not in r)
        print(f"Individual Crawls: {successful}/{len(self.test_urls)} successful")
        
        if "error" not in batch_result:
            print(f"Batch Crawl: {batch_result.get('completed', 0)}/{batch_result.get('total', 0)} successful")
        else:
            print(f"Batch Crawl: Failed ({batch_result.get('error', 'Unknown error')})")
        
        print(f"\n🎉 Tests completed at {datetime.now()}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test runner."""
    tester = CrawlerTester()
    try:
        await tester.run_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
