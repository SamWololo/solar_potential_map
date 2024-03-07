import numpy as np
import streamlit as st
import googlemaps as gm
import requests
from PIL import Image
#import gdown
import cv2
from utils.params import *
from utils.utils import *

#interact with endpoint
if API_RUN == 'LOCAL':
    api_url = 'http://127.0.0.1:8000'
    API_KEY = MAPS_API_KEY
elif st.secrets['API_RUN'] == "ONLINE":
    api_url = "https://project-image-eumqyi7yoa-an.a.run.app/"
    API_KEY = st.secrets["MAPS_API_KEY"]
endpoint = '/predict'


def send_backend(lat, lng, zoom, fast_url):
    """
    Capture google maps image, put that in list form in a dict
    and send to the fast API back end
    """
    image = get_gmaps_image(lat, lng, zoom)
    image_np = np.array(image)
    data = {'image': image_np.tolist()}

    r = requests.post(url=fast_url,
                      json=data)

    return r

if 'clicked' not in st.session_state:
    st.session_state.clicked = False

def click_button():
    """Stateful button, allows the page to change to the
    image + mask when button is clicked"""
    st.session_state.clicked = True

def click_reset():
    """Resets page, lets calculation button be clicked again"""
    st.session_state.clicked = False

def main():

    #LAYOUT / CONFIG
    #set page configuration to wide
    st.set_page_config(layout="wide",initial_sidebar_state="collapsed")

    #shrink the page margins
    margins_css = """
        <style>
            .main > div {
                padding-top: 0rem;
                padding-left: 5rem;
                padding-right: 3rem;
            }
        </style>
    """

    #markdown for button color
    button_color = st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: rgb(195, 27, 27);
            height: 3em;
            width: 6em;
        }
        </style>""", unsafe_allow_html=True)

    hover_color = st.markdown("""
        <style>
        div.stButton > button:hover {
            background-color: #ff000050;
        }
        </style>""", unsafe_allow_html=True)

    st.markdown(margins_css, unsafe_allow_html=True)

    #markdown color for sidebar
    st.markdown("""
        <style>
            [data-testid=stSidebar] {
                background-color: #ff000050;
            }
        </style>
        """, unsafe_allow_html=True)

    st.markdown(
        """
        <style>
            div[data-testid="column"]:nth-of-type(1)
            {
                text-align: center;
            }

        </style>
        """,unsafe_allow_html=True
        )

    st.markdown(
        """
        <style>
            div[data-testid="column"]:nth-of-type(3)
            {
                text-align: center;
            }

        </style>
        """,unsafe_allow_html=True
        )

    # Set up the page title
    st.title("Solar Potential Map")

    # Initialize Google Maps API client
    gmaps = gm.Client(key=API_KEY)

    with st.sidebar:
        st.subheader("How much solar power can the rooftops of an area generate?")
        st.divider()


    #Establish column layout, details in left small column, map in larger right column
    col1, col2, col3= st.columns([4, 0.5, 5.5])

    with col1:
        st.write('')
        location = st.text_input("Enter location or address:", 'Le Wagon, Meguro, Tokyo')
        zoom_level = st.slider("Zoom level:", 17, 20, 18)

    # Geocode location to get latitude and longitude
    geocode_result = gmaps.geocode(location)
    if geocode_result:
        lat = geocode_result[0]['geometry']['location']['lat']
        lng = geocode_result[0]['geometry']['location']['lng']
        zipcode = geocode_result[0]['address_components'][0]['long_name']
        neighborhood = geocode_result[0]['address_components'][3]['long_name']
        city_name = geocode_result[0]['address_components'][4]['long_name']
        prefecture_name = geocode_result[0]['address_components'][5]['long_name']

        valid_cities = ["tokyo","osaka","nagoya","fukuoka","sapporo"]
        if city_name not in valid_cities:
            city_name = 'tokyo'
        address = ""
        for component in geocode_result[0]['address_components']:
            address += component['long_name'] + " "
        address = address.strip()

    else:
        st.error("Error: Location not found.")
        st.stop()

    with col1:
        placeholder = False
        sub_col_1, sub_col_2 = st.columns([3,3])
        with sub_col_1:
            if st.button("Calculate!", on_click=click_button):
                #this is where the back end call will go
                original_image = get_gmaps_image(lat, lng, zoom_level)
                #mask_array = original_image
                new_url = api_url+endpoint
                request_post= send_backend(lat=lat, lng=lng, zoom=zoom_level, fast_url=new_url)
                mask_json = request_post.json()
                mask_array = np.array(mask_json['output_mask'])
                mask = cv2.normalize(mask_array, dst=None, alpha=0,
                                beta=255,norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                mask = smooth_image(mask, 900)

                #calculations
                sqrm = np.rint(rooftop_area_calculator(zoom=zoom_level, lat=lat, mask=mask_array)).astype(np.int32)
                #need to add a city grabber to pass through the energy output function, default is tokyo
                solar_kw = np.rint(solar_panel_energy_output(area=sqrm, location=city_name)).astype(np.int32)
                co2 = np.rint(co2_calculator(solar_panel_output = solar_kw)["Coal Offset"]).astype(np.int32)
                car_equiv = str(np.rint(car_equivalent(co2)).astype(np.int32))
                homes = str(np.rint(home_electricity(solar_kw)).astype(np.int32))
                placeholder = True
        with sub_col_2:
            if st.session_state.clicked:
                #help="Click to calculate a different area!"
                if st.button("Reset", on_click=click_reset):
                    placeholder = False
                    st.components.v1.html(map_html, width=650, height=500)

        st.write('')
        st.write(f'Totals for {neighborhood.capitalize()}, {city_name.capitalize()}')
        #area for calculation totals

        sub_col_3, sub_col_4, sub_col_5 = st.columns([3,1,3])
        with sub_col_3:
            with st.container():
                # html_code = """<div id = 'inner_container'></div>"""
                # st.markdown(html_code, unsafe_allow_html=True)
                if not placeholder:
                    #When placeholder is False then this will display
                    st.write(f"Square meters: 0 m²")
                    st.write("")
                    st.write(f"Energy: 0 Kw hours")
                    st.write('')
                    st.write(f"CO2 offset: 0 metric tons")
                if placeholder:
                    #When placeholder is True this will display, conditional formatting
                    if len(str(sqrm)) <= 3:
                        st.write(f"Square meters: {str(sqrm)} m²")
                    elif len(str(sqrm)) == 4:
                        st.write(f"Square meters: {str(sqrm)[:1]},{str(sqrm)[1:]} m²")
                    elif len(str(sqrm)) == 5:
                        st.write(f"Square meters: {str(sqrm)[:2]},{str(sqrm)[2:]} m²")
                    elif len(str(sqrm)) == 6:
                        st.write(f"Square meters: {str(sqrm)[:3]},{str(sqrm)[3:]} m²")
                    st.write("")
                    if len(str(solar_kw)) < 10:
                        st.write(f"Energy: {str(solar_kw)[:-6]} million kWh per year")
                    elif len(str(solar_kw)) >= 10:
                        st.write(f"Energy: {str(solar_kw)[0]},{str(solar_kw)[1:4]} million kWh per year")
                    st.write("")
                    if str(co2)[0] == "1":
                        st.write(f"CO2 offset: {str(co2)[:-6]} metric ton")
                    elif str(co2)[0] != "1":
                        st.write(f"CO2 offset: {str(co2)[:-6]} metric tons")
        with sub_col_4:
            with st.container():
                if not st.session_state.clicked:
                    st.write("")
                else:
                    st.write("")
                    st.write("")
                    #st.write("")
                    st.image("st_images/red_home.png", width=40)
                    st.image("st_images/red_car.png", width=40)
        with sub_col_5:
            with st.container():
                if not st.session_state.clicked:
                    st.write("")
                else:
                    st.write("")
                    st.write("")
                    #st.write("")
                    if len(homes) <= 3:
                        st.write(f"This would power {homes} homes for a year!")
                    elif len(homes) == 4:
                        st.write(f"This would power {homes[:1]},{homes[1:]} homes for a year!")
                    elif len(homes) == 5:
                        st.write(f"This would power {homes[:2]},{homes[2:]} homes for a year!")
                    st.write("")
                    if len(car_equiv) <= 3:
                        st.write(f"That's {car_equiv} cars driving for one year!")
                    elif len(car_equiv) == 4:
                        st.write(f"That's {car_equiv[:1]},{car_equiv[1:]} cars driving for one year!")

    with col2:
        #middle column, just white space to add a more balanced look
        st.write("")

    # Build Html/JS code to visualize the map using Google Maps API:
    map_html = f"""
        <div id="map" style="width: 100%; height:500px;"></div>
        <script>
            var lat = {lat};
            var lng = {lng};
            function initMap() {{
                var geocoder = new google.maps.Geocoder();
                var address = "{location}";
                geocoder.geocode({{ 'address': address }}, function(results, status) {{
                    if (status === 'OK') {{
                        var map = new google.maps.Map(document.getElementById('map'), {{
                            zoom: {zoom_level},
                            mapTypeId: 'satellite',
                            tilt: 0,
                            center: results[0].geometry.location
                        }});
                        // Enable the map type control
                        var mapTypeControlOptions = {{
                            style: google.maps.MapTypeControlStyle.DEFAULT,
                            position: google.maps.ControlPosition.TOP_RIGHT
                        }};
                        map.setOptions({{ mapTypeControl: true, mapTypeControlOptions: mapTypeControlOptions }});

                        square.setMap(map);
                    }} else {{
                        alert('Geocode was not successful for the following reason: ' + status);
                    }}
                }});
            }}

        </script>
        <script async defer src="https://maps.googleapis.com/maps/api/js?key={API_KEY}&callback=initMap"></script>
    """

    # Display the map:
    with col3:
        st.markdown(
            """
            <style>
                button[title^=Exit]+div [data-testid=stImage]{
                    text-align: center;
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                    width: 100%;
                }
            </style>
            """, unsafe_allow_html=True
        )
        if not st.session_state.clicked:
            st.components.v1.html(map_html, width=650, height=500)
        else:
            sub_col_6, sub_col_7 = st.columns([4,4])
            with sub_col_6:
                st.write("Original")
                st.image([original_image], use_column_width=True)
            with sub_col_7:
                st.write("Mask")
                st.image([mask], use_column_width=True)


if __name__ == "__main__":
    main()
