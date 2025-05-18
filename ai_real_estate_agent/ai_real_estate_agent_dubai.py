from typing import Dict, List
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from firecrawl import FirecrawlApp
import streamlit as st

class PropertyData(BaseModel):
    """Schema for property data extraction"""
    building_name: str = Field(description="Name of the building/property", alias="Building_name")
    property_type: str = Field(description="Type of property (commercial, residential, etc)", alias="Property_type")
    location_address: str = Field(description="Complete address of the property")
    price: str = Field(description="Price of the property", alias="Price")
    Size: str = Field(description="Size of the property", alias="Size")
    description: str = Field(description="Detailed description of the property", alias="Description")
    property_link: str = Field(description="link to the property", alias="property_link")

class PropertiesResponse(BaseModel):
    """Schema for multiple properties response"""
    properties: List[PropertyData] = Field(description="List of property details")

class LocationData(BaseModel):
    """Schema for location price trends"""
    location: str
    price_per_sqft: float
    percent_increase: float
    rental_yield: float

class LocationsResponse(BaseModel):
    """Schema for multiple locations response"""
    locations: List[LocationData] = Field(description="List of location data points")

class FirecrawlResponse(BaseModel):
    """Schema for Firecrawl API response"""
    success: bool
    data: Dict
    status: str
    expiresAt: str

class PropertyFindingAgent:
    """Agent responsible for finding properties and providing recommendations"""
    
    def __init__(self, firecrawl_api_key: str="fc-2ac1e59211e445c1a36ad75af184397c", openai_api_key: str ="AIzaSyAwKw-J7hZTKh_7NUUEv6EDY281K9p7x-w", model_id: str = "gemini-2.0-flash-exp"):
        self.agent = Agent(
            model=Gemini(id=model_id, api_key=openai_api_key),
            markdown=True,
            description="I am a real estate expert who helps find and analyze properties based on user preferences."
        )
        self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)

    def find_properties(
        self, 
        city: str,
        max_price: float,
        property_category: str = "Residential",
        property_type: str = "Flat"
    ) -> str:
        """Find and analyze properties based on user preferences"""
        formatted_location = city.strip().lower().replace(" ", "-")
        formatted_property_type = property_type.strip().lower().replace(" ", "-")
        
        urls = [
             f"https://www.propertyfinder.ae/en/buy/dubai/{formatted_property_type}-for-sale-{formatted_location}.html",
            # f"https://www.bayut.com/for-sale/{formatted_property_type}/dubai/{formatted_location}/",
            # f"https://famproperties.com/{formatted_property_type}-for-sale-in-{formatted_location}-dubai"
        ]
        print("Urls:", urls)
        
        raw_response = self.firecrawl.extract(
            urls=urls,
            params={
                'prompt': f"""Extract ONLY 10 OR LESS different {property_category} {property_type} along with property link from {city} that cost less than {max_price} millions.
                
                Requirements:
                - Property Category: {property_category} properties only
                - Property Type: {property_type} only
                - Location: {city}
                - Maximum Price: {max_price} Millions
                - Include complete property details with exact location
                - IMPORTANT: Return data for at least 3 different properties. MAXIMUM 10. must mix the property list from all urls.
                - Format as a list of properties with their respective details
                """,
                'schema': PropertiesResponse.model_json_schema()
            }
        )
        
        print("Raw Property Response:", raw_response)
        
        if isinstance(raw_response, dict) and raw_response.get('success'):
            properties = raw_response['data'].get('properties', [])
        else:
            properties = []
            
        print("Processed Properties:", properties)

        
        analysis = self.agent.run(
            f"""As a real estate expert, analyze these properties and market trends:

            Properties Found in json format:
            {properties}

            **IMPORTANT INSTRUCTIONS:**
            1. ONLY analyze properties from the above JSON data that match the user's requirements:
               - Property Category: {property_category}
               - Property Type: {property_type}
               - Maximum Price: {max_price} millions
            2. DO NOT create new categories or property types
            3. From the matching properties, select 5-6 properties with prices closest to {max_price} millions

            Please provide your analysis in this format:
            
            🏠 SELECTED PROPERTIES
            • List only 5-6 best matching properties with prices closest to {max_price} millions
            • For each property include:
              - Name and Location along with link to the property as cta button
              - Price (with value analysis)
              - Key Features
              - Pros and Cons

            💰 BEST VALUE ANALYSIS
            • Compare the selected properties based on:
              - Price per sq ft
              - Location advantage
              - Amenities offered

            📍 LOCATION INSIGHTS
            • Specific advantages of the areas where selected properties are located

            💡 RECOMMENDATIONS
            • Top 3 properties from the selection with reasoning
            • Investment potential
            • Points to consider before purchase

            🤝 NEGOTIATION TIPS
            • Property-specific negotiation strategies

            Format your response in a clear, structured way using the above sections.
            """
        )
        
        return analysis.content

    def get_location_trends(self, city: str) -> str:
        """Get price trends for different localities in the city"""
        formatted_location = city.strip().lower().replace(" ", "-")
        trndurl=[
            f"https://www.propertyfinder.ae/en/area-insights/dubai/{formatted_location}",
        ]
        print("Trend Url:", trndurl)
        raw_response = self.firecrawl.extract(
            urls=trndurl, 
            params={
            'prompt': """Extract price trends data for ALL major localities in the city. 
            IMPORTANT: 
            - Return data for at least 5-10 different localities
            - Include both premium and affordable areas
            - Do not skip any locality mentioned in the source
            - Format as a list of locations with their respective data
            """,
            'schema': LocationsResponse.model_json_schema(),
        })
        print("Trend raw resonse:", raw_response);
        if isinstance(raw_response, dict) and raw_response.get('success'):
            locations = raw_response['data'].get('locations', [])
    
            analysis = self.agent.run(
                f"""As a real estate expert, analyze these location price trends for {city}:

                {locations}

                Please provide:
                1. A bullet-point summary of the price trends for each location
                2. Identify the top 3 locations with:
                   - Highest price appreciation
                   - Best rental yields
                   - Best value for money
                3. Investment recommendations:
                   - Best locations for long-term investment
                   - Best locations for rental income
                   - Areas showing emerging potential
                4. Specific advice for investors based on these trends

                Format the response as follows:
                
                📊 LOCATION TRENDS SUMMARY
                • [Bullet points for each location]

                🏆 TOP PERFORMING AREAS
                • [Bullet points for best areas]

                💡 INVESTMENT INSIGHTS
                • [Bullet points with investment advice]

                🎯 RECOMMENDATIONS
                • [Bullet points with specific recommendations]
                """
            )
            
            return analysis.content
            
        return "No price trends data available"

def create_property_agent():
    """Create PropertyFindingAgent with API keys from session state"""
    if 'property_agent' not in st.session_state:
        # st.session_state.property_agent = PropertyFindingAgent(
        #     firecrawl_api_key=st.session_state.firecrawl_key,
        #     openai_api_key=st.session_state.openai_key,
        #     model_id=st.session_state.model_id
        # )
        st.session_state.property_agent = PropertyFindingAgent()

def main():
    st.set_page_config(
        page_title="AI Real Estate Agent",
        page_icon="🏠",
        layout="wide"
    )

    # with st.sidebar:
    #     st.title("🔑 API Configuration")
        
    #     st.subheader("🤖 Model Selection")
    #     model_id = st.selectbox(
    #         "Choose OpenAI Model",
    #         options=["o3-mini", "gpt-4o"],
    #         help="Select the AI model to use. Choose gpt-4o if your api doesn't have access to o3-mini"
    #     )
    #     st.session_state.model_id = model_id
        
    #     st.divider()
        
    #     st.subheader("🔐 API Keys")
    #     firecrawl_key = st.text_input(
    #         "Firecrawl API Key",
    #         type="password",
    #         help="Enter your Firecrawl API key"
    #     )
    #     openai_key = st.text_input(
    #         "OpenAI API Key",
    #         type="password",
    #         help="Enter your OpenAI API key"
    #     )
        
    #     if firecrawl_key and openai_key:
    #         st.session_state.firecrawl_key = firecrawl_key
    #         st.session_state.openai_key = openai_key
    create_property_agent()

    st.title("🏠 Dubai's AI Real Estate Agent")
    st.info(
        """
        Welcome to the Dubai's AI Real Estate Agent! 
        Enter your search criteria below to get property recommendations 
        and location insights.
        """
    )

    col1, col2 = st.columns(2)
    
    with col1:
        city = st.text_input(
            "Area",
            placeholder="Enter area name (e.g., Business Bay)",
            help="Enter the area where you want to search for properties"
        )
        
        property_category = st.selectbox(
            "Property Category",
            options=["Residential", "Commercial"],
            help="Select the type of property you're interested in"
        )

    with col2:
        max_price = st.number_input(
            "Maximum Price (in millions)",
            min_value=0.1,
            max_value=100.0,
            value=10.0,
            step=0.1,
            help="Enter your maximum budget in millions"
        )
        
        property_type = st.selectbox(
            "Property Type",
            options=["Apartments","Villas"],
            help="Select the specific type of property"
        )

    if st.button("🔍 Start Search", use_container_width=True):
        # if 'property_agent' not in st.session_state:
        #     st.error("⚠️ Please enter your API keys in the sidebar first!")
        #     return
            
        if not city:
            st.error("⚠️ Please enter a area name!")
            return
            
        try:
            with st.spinner("🔍 Searching for properties..."):
                property_results = st.session_state.property_agent.find_properties(
                    city=city,
                    max_price=max_price,
                    property_category=property_category,
                    property_type=property_type
                )
                
                st.success("✅ Property search completed!")
                
                st.subheader("🏘️ Property Recommendations")
                st.markdown(property_results)
                
                st.divider()
                
                with st.spinner("📊 Analyzing location trends..."):
                    location_trends = st.session_state.property_agent.get_location_trends(city)
                    
                    st.success("✅ Location analysis completed!")
                    
                    with st.expander("📈 Location Trends Analysis of the city"):
                        st.markdown(location_trends)
                
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
