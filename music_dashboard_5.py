import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2

st.set_page_config(page_title="Music Evolution", page_icon="🎵", layout="wide")
st.title("🎵 Music Evolution Analysis")
st.caption("MusicBrainz Database · PostgreSQL 15 · M1 IPP S2")

# ─── Connection ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host="localhost", port=5432,
        database="musicbrainz",
        user="postgres", password="password"
    )

def query(sql):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql)
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows, columns=cols)

def query_params(sql, params):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    return pd.DataFrame(rows, columns=cols)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "🌍 Geography",
    "🤝 Relationships",
    "🎸 Bands",
    "🎓 Teacher Influence",
    "🗺️ Artist Network Map"
])

# ─── TAB 1: Overview ──────────────────────────────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Artists", f"{query('SELECT COUNT(*) as c FROM artist')['c'][0]:,}")
    col2.metric("Release Groups", f"{query('SELECT COUNT(*) as c FROM release_group')['c'][0]:,}")
    col3.metric("Relationships", f"{query('SELECT COUNT(*) as c FROM l_artist_artist')['c'][0]:,}")

    st.divider()
    st.subheader("Top 15 Genres")
    df = query("""
        SELECT t.name AS genre, COUNT(*) AS artists
        FROM artist_tag at2
        JOIN tag t ON at2.tag = t.id
        GROUP BY t.name ORDER BY artists DESC LIMIT 15
    """)
    st.plotly_chart(
        px.bar(df, x='genre', y='artists', color='artists',
               color_continuous_scale='Blues'),
        width='stretch'
    )

# ─── TAB 2: Geography ─────────────────────────────────────────────────────────
with tab2:
    st.subheader("Artists per Country")
    df = query("""
        SELECT ar.name AS country, COUNT(*) AS artists
        FROM artist a
        JOIN area ar ON a.area = ar.id
        JOIN area_type at ON ar.type = at.id
        WHERE at.name = 'Country'
        GROUP BY ar.name ORDER BY artists DESC LIMIT 20
    """)
    st.plotly_chart(
        px.bar(df, x='country', y='artists', color='artists',
               color_continuous_scale='Blues'),
        width='stretch'
    )

    st.subheader("Most Popular Genre per Country")
    df2 = query("""
        SELECT DISTINCT ON (ar.name)
            ar.name AS country,
            t.name AS genre,
            COUNT(*) AS count
        FROM artist_tag at2
        JOIN tag t ON at2.tag = t.id
        JOIN artist a ON at2.artist = a.id
        JOIN area ar ON a.area = ar.id
        JOIN area_type atype ON ar.type = atype.id
        WHERE atype.name = 'Country'
        GROUP BY ar.name, t.name
        ORDER BY ar.name, count DESC
    """)
    st.plotly_chart(
        px.choropleth(df2, locations='country', locationmode='country names',
                      color='genre', hover_name='country', height=500),
        width='stretch'
    )

# ─── TAB 3: Relationships ─────────────────────────────────────────────────────
with tab3:
    st.subheader("Relationship Types")
    df = query("""
        SELECT lt.name, COUNT(*) as count
        FROM l_artist_artist laa
        JOIN link l ON laa.link = l.id
        JOIN link_type lt ON l.link_type = lt.id
        GROUP BY lt.name ORDER BY count DESC
    """)
    st.plotly_chart(
        px.bar(df, x='count', y='name', orientation='h',
               color='count', color_continuous_scale='Blues'),
        width='stretch'
    )

    st.subheader("Most Influential Teachers")
    df2 = query("""
        SELECT a1.name AS teacher, COUNT(*) AS students
        FROM l_artist_artist laa
        JOIN link l ON laa.link = l.id
        JOIN link_type lt ON l.link_type = lt.id
        JOIN artist a1 ON laa.entity0 = a1.id
        WHERE lt.name = 'teacher'
        GROUP BY a1.name ORDER BY students DESC LIMIT 15
    """)
    st.plotly_chart(
        px.bar(df2, x='students', y='teacher', orientation='h',
               color='students', color_continuous_scale='Blues'),
        width='stretch'
    )

# ─── TAB 4: Bands ─────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Biggest Bands by Member Count")
    df = query("""
        SELECT a2.name AS band, COUNT(*) AS members
        FROM l_artist_artist laa
        JOIN link l ON laa.link = l.id
        JOIN link_type lt ON l.link_type = lt.id
        JOIN artist a1 ON laa.entity0 = a1.id
        JOIN artist a2 ON laa.entity1 = a2.id
        WHERE lt.name = 'member of band'
        GROUP BY a2.name ORDER BY members DESC LIMIT 15
    """)
    st.plotly_chart(
        px.bar(df, x='members', y='band', orientation='h',
               color='members', color_continuous_scale='Blues'),
        width='stretch'
    )

    st.subheader("Search a Band")
    band = st.text_input("Band name", "Beatles")
    if band:
        df2 = query_params("""
            SELECT a1.name AS member, a2.name AS band
            FROM l_artist_artist laa
            JOIN link l ON laa.link = l.id
            JOIN link_type lt ON l.link_type = lt.id
            JOIN artist a1 ON laa.entity0 = a1.id
            JOIN artist a2 ON laa.entity1 = a2.id
            WHERE lt.name = 'member of band'
            AND a2.name ILIKE %s
            LIMIT 20
        """, (f'%{band}%',))
        if df2.empty:
            st.warning("No results found")
        else:
            st.dataframe(df2, width='stretch')

# ─── TAB 5: Teacher Influence ─────────────────────────────────────────────────
with tab5:
    st.subheader("Genre Transmission Through Teaching")
    st.caption("How musical genres spread across generations of students")

    col1, col2 = st.columns([2, 1])
    with col1:
        teacher_name = st.text_input("Teacher name", "Nadia Boulanger")
    with col2:
        max_depth = st.slider("Generations", min_value=1, max_value=5, value=4)

    if teacher_name:
        # Check teacher exists
        teacher_check = query_params(
            "SELECT id, name FROM artist WHERE name = %s LIMIT 1",
            (teacher_name,)
        )

        if teacher_check.empty:
            st.warning(f"Artist '{teacher_name}' not found in the database.")
        else:
            teacher_id = int(teacher_check['id'][0])
            st.success(f"Found: **{teacher_check['name'][0]}** (id: {teacher_id})")

            # Genre distribution per generation
            df_genres = query_params(f"""
                WITH RECURSIVE teacher_chain AS (
                    SELECT entity0, entity1, 1 AS depth, ARRAY[entity0] AS visited
                    FROM l_artist_artist laa
                    JOIN link l ON laa.link = l.id
                    JOIN link_type lt ON l.link_type = lt.id
                    WHERE lt.name = 'teacher'
                    AND entity0 = %s

                    UNION ALL

                    SELECT laa.entity0, laa.entity1, tc.depth + 1, tc.visited || laa.entity0
                    FROM l_artist_artist laa
                    JOIN link l ON laa.link = l.id
                    JOIN link_type lt ON l.link_type = lt.id
                    JOIN teacher_chain tc ON laa.entity0 = tc.entity1
                    WHERE lt.name = 'teacher'
                    AND tc.depth < {max_depth}
                    AND NOT laa.entity0 = ANY(tc.visited)
                )
                SELECT
                    tc.depth AS generation,
                    t.name AS genre,
                    COUNT(DISTINCT a.id) AS student_count
                FROM teacher_chain tc
                JOIN artist a ON tc.entity1 = a.id
                JOIN artist_tag at2 ON at2.artist = a.id
                JOIN tag t ON at2.tag = t.id
                GROUP BY tc.depth, t.name
                ORDER BY tc.depth, student_count DESC
            """, (teacher_id,))

            if df_genres.empty:
                st.warning("No genre data found for this teacher's students.")
            else:
                # Top genres per generation bar chart
                st.subheader(f"Top Genres by Generation — {teacher_name}")
                top_genres = df_genres.groupby('genre')['student_count'].sum().nlargest(10).index.tolist()
                df_top = df_genres[df_genres['genre'].isin(top_genres)]

                fig = px.bar(
                    df_top,
                    x='generation', y='student_count',
                    color='genre', barmode='group',
                    labels={'generation': 'Generation', 'student_count': 'Students', 'genre': 'Genre'},
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1, tickfont=dict(color='black'), title_font=dict(color='black')),
                    plot_bgcolor='white', paper_bgcolor='white',
                    font=dict(color='black'),
                    legend=dict(font=dict(color='black'), bgcolor='white')
                )
                st.plotly_chart(fig, width='stretch')

                # Students per generation
                st.subheader("Students per Generation")
                df_students = query_params(f"""
                    WITH RECURSIVE teacher_chain AS (
                        SELECT entity0, entity1, 1 AS depth, ARRAY[entity0] AS visited
                        FROM l_artist_artist laa
                        JOIN link l ON laa.link = l.id
                        JOIN link_type lt ON l.link_type = lt.id
                        WHERE lt.name = 'teacher'
                        AND entity0 = %s
                        UNION ALL
                        SELECT laa.entity0, laa.entity1, tc.depth + 1, tc.visited || laa.entity0
                        FROM l_artist_artist laa
                        JOIN link l ON laa.link = l.id
                        JOIN link_type lt ON l.link_type = lt.id
                        JOIN teacher_chain tc ON laa.entity0 = tc.entity1
                        WHERE lt.name = 'teacher'
                        AND tc.depth < {max_depth}
                        AND NOT laa.entity0 = ANY(tc.visited)
                    )
                    SELECT depth AS generation, COUNT(DISTINCT entity1) AS students
                    FROM teacher_chain
                    GROUP BY depth
                    ORDER BY depth
                """, (teacher_id,))

                fig2 = px.bar(
                    df_students, x='generation', y='students',
                    color='students', color_continuous_scale='Blues',
                    labels={'generation': 'Generation', 'students': 'Number of Students'}
                )
                fig2.update_layout(
                    xaxis=dict(tickmode='linear', dtick=1),
                    plot_bgcolor='white', paper_bgcolor='white',
                    font=dict(color='black'),
                    coloraxis=dict(
                        colorbar=dict(
                            tickfont=dict(color='black'),
                            title=dict(font=dict(color='black'))
                        )
                    )
                )
                st.plotly_chart(fig2, width='stretch')

                # Raw data table
                with st.expander("See full data"):
                    st.dataframe(df_genres, width='stretch')

# ─── TAB 6: Artist Network Map ────────────────────────────────────────────────
with tab6:
    import plotly.graph_objects as go
    import random

    st.subheader("Geographic Network Map")
    st.caption("Explore artist connections radiating from a starting artist on a map")

    col1, col2 = st.columns([2, 1])
    with col1:
        map_artist = st.text_input("Starting artist", "Louis Armstrong")
    with col2:
        map_depth = st.slider("Network depth", min_value=1, max_value=5, value=3, key="map_depth")

    city_coords = {
        "Hudson": (42.2529, -73.7882),
        "Washington, D.C.": (38.9072, -77.0369),
        "Bloomington": (40.4842, -88.9937),
        "Easton": (40.6884, -75.2207),
        "Pratt": (37.6436, -98.7398),
        "New York": (40.7128, -74.0060),
        "New York City": (40.7128, -74.0060),
        "Chicago": (41.8781, -87.6298),
        "New Orleans": (29.9511, -90.0715),
        "Los Angeles": (34.0522, -118.2437),
        "Boston": (42.3601, -71.0589),
        "Philadelphia": (39.9526, -75.1652),
        "Nashville": (36.1627, -86.7816),
        "Detroit": (42.3314, -83.0458),
        "Atlanta": (33.7490, -84.3880),
        "San Francisco": (37.7749, -122.4194),
        "London": (51.5074, -0.1278),
        "Paris": (48.8566, 2.3522),
        "Berlin": (52.5200, 13.4050),
        "Toronto": (43.6532, -79.3832),
        "Sedalia": (38.7045, -93.2283),
        "Texarkana": (33.4418, -94.0377),
        "St. Louis": (38.6270, -90.1994),
    }

    country_coords = {
        "United States": (39.5, -98.35),
        "United Kingdom": (55.3781, -3.4360),
        "France": (46.2276, 2.2137),
        "Germany": (51.1657, 10.4515),
        "Canada": (56.1304, -106.3468),
        "Japan": (36.2048, 138.2529),
        "Australia": (-25.2744, 133.7751),
    }

    def get_coords(city, country):
        if city and city in city_coords:
            return city_coords[city]
        if country and country in country_coords:
            random.seed(hash(str(city) + str(country)))
            lat, lon = country_coords[country]
            return (lat + random.uniform(-2, 2), lon + random.uniform(-2, 2))
        return None

    if map_artist:
        artist_row = query_params(
            "SELECT id, name, begin_date_year FROM artist WHERE name = %s LIMIT 1",
            (map_artist,)
        )

        if artist_row.empty:
            st.warning(f"Artist '{map_artist}' not found.")
        else:
            artist_id = int(artist_row['id'][0])
            artist_year = artist_row['begin_date_year'][0]
            st.success(f"Found: **{artist_row['name'][0]}** (born: {artist_year})")

            with st.spinner("Building network map..."):
                df_net = query_params(f"""
                    WITH RECURSIVE artist_network AS (
                        SELECT 
                            %s::integer AS artist_id,
                            %s::integer AS parent_id,
                            ARRAY[%s::integer] AS visited,
                            0 AS depth,
                            ''::varchar AS relationship
                        UNION ALL
                        SELECT 
                            CASE WHEN laa.entity0 = an.artist_id 
                                 THEN laa.entity1 ELSE laa.entity0 END,
                            an.artist_id,
                            an.visited || CASE WHEN laa.entity0 = an.artist_id 
                                               THEN laa.entity1 ELSE laa.entity0 END,
                            an.depth + 1,
                            lt.name::varchar
                        FROM artist_network an
                        JOIN l_artist_artist laa ON laa.entity0 = an.artist_id 
                                                 OR laa.entity1 = an.artist_id
                        JOIN link l ON laa.link = l.id
                        JOIN link_type lt ON l.link_type = lt.id
                        WHERE an.depth < {map_depth}
                        AND NOT CASE WHEN laa.entity0 = an.artist_id 
                                     THEN laa.entity1 ELSE laa.entity0 END = ANY(an.visited)
                    )
                    SELECT DISTINCT ON (an.artist_id)
                        a.id AS artist_id,
                        a.name AS artist,
                        a.begin_date_year,
                        ar.name AS country,
                        ar2.name AS city,
                        an.depth,
                        an.parent_id,
                        an.relationship
                    FROM artist_network an
                    JOIN artist a ON an.artist_id = a.id
                    LEFT JOIN area ar ON a.area = ar.id
                    LEFT JOIN area ar2 ON a.begin_area = ar2.id
                    ORDER BY an.artist_id, an.depth
                """, (artist_id, artist_id, artist_id))

                df_net['coords'] = df_net.apply(lambda r: get_coords(r['city'], r['country']), axis=1)
                df_net['lat'] = df_net['coords'].apply(lambda c: c[0] if c else None)
                df_net['lon'] = df_net['coords'].apply(lambda c: c[1] if c else None)
                df_mapped = df_net[df_net['lat'].notna()].copy()

                st.info(f"Network: {len(df_net)} artists total, {len(df_mapped)} plotted on map")

                if df_mapped.empty:
                    st.warning("No geographic data found for this artist's network.")
                else:
                    depth_colors = {
                        0: "#1B3A6B", 1: "#2B6CB0", 2: "#3182CE",
                        3: "#4299E1", 4: "#63B3ED", 5: "#90CDF4",
                    }
                    parent_map = df_mapped.set_index('artist_id')[['lat', 'lon']].to_dict('index')

                    map_fig = go.Figure()

                    # Edges
                    edge_lons, edge_lats = [], []
                    for _, row in df_mapped.iterrows():
                        if row['depth'] > 0 and row['parent_id'] in parent_map:
                            p = parent_map[row['parent_id']]
                            edge_lons += [p['lon'], row['lon'], None]
                            edge_lats += [p['lat'], row['lat'], None]

                    map_fig.add_trace(go.Scattergeo(
                        lon=edge_lons, lat=edge_lats,
                        mode='lines',
                        line=dict(width=1, color='#A0AEC0'),
                        hoverinfo='none', showlegend=False
                    ))

                    # Nodes per depth
                    for d in sorted(df_mapped['depth'].unique()):
                        sub = df_mapped[df_mapped['depth'] == d]
                        size = 16 if d == 0 else max(7, 13 - d * 2)
                        map_fig.add_trace(go.Scattergeo(
                            lon=sub['lon'], lat=sub['lat'],
                            mode='markers+text',
                            marker=dict(size=size, color=depth_colors.get(d, "#718096"),
                                       line=dict(width=1.5, color='white'), opacity=0.9),
                            text=sub['artist'],
                            textposition='top center',
                            textfont=dict(size=8 if d > 0 else 10, color='#1A202C'),
                            customdata=sub[['city', 'country', 'begin_date_year', 'relationship']].fillna('Unknown').values,
                            hovertemplate=(
                                "<b>%{text}</b><br>"
                                "City: %{customdata[0]}<br>"
                                "Country: %{customdata[1]}<br>"
                                "Born: %{customdata[2]}<br>"
                                "Relationship: %{customdata[3]}<extra></extra>"
                            ),
                            name=map_artist if d == 0 else f"Depth {d}"
                        ))

                    map_fig.update_layout(
                        title=dict(
                            text=f"Geographic Network of {map_artist} (depth={map_depth})",
                            x=0.5, font=dict(size=14, color='#1B3A6B')
                        ),
                        geo=dict(
                            scope='north america',
                            showland=True, landcolor='#F7FAFC',
                            showocean=True, oceancolor='#DBEAFE',
                            showcoastlines=True, coastlinecolor='#CBD5E0',
                            showcountries=True, countrycolor='#CBD5E0',
                            projection_type='albers usa',
                        ),
                        legend=dict(
                            x=0.01, y=0.95,
                            bgcolor='rgba(255,255,255,0.9)',
                            bordercolor='#CBD5E0', borderwidth=1,
                            font=dict(size=11, color='black')
                        ),
                        paper_bgcolor='white',
                        height=600,
                        margin=dict(l=0, r=0, t=60, b=0)
                    )

                    st.plotly_chart(map_fig, width='stretch')
