![Architecture Diagram](./architecture.svg)

This repository contains parts of a university group project from the course "Advanced Distributed Systems Prototyping" (Spring 2024). 
Most of the code that can be found in this repository was written by me. 
The goal was to develop a web-application to visualize the real-time wind conditions for a city in a 3D model (kinda like Google Earth), backed by a cloud-native backend. I was a member of the backend team.

The wind data can be imagined as a number of 2D grids stacked on top of each other (one for each altitude layer).
Each cell contains a wind vector, representing wind direction and speed. At the most fine-grained resolution, one grid cell has a size of 2m x 2m. 

The real-time wind data is generated through a process called "POD interpolation", using a pre-computed
wind model and the wind information from a reference sensor somewhere in the city. The POD wind model consists of about 36 parameters for each cell. Cells can be interpolated individually.

As serving wind data for an entire city at a 2m x 2m resolution would be infeasible, we implemented a downsampling procedure similar to image downsampling. To do that efficiently, we pre-compute the wind models at multiple resolutions (4m x 4m, 8m x 8m, ...), to interpolate directly at a desired resolution.To enable efficient bulk-retrieval of parts of the wind model, we store it in the form of chunk files in Google Cloud Storage.
The chunking is done according to the S2 geo-indexing method from Google, which makes it possible to cluster the grid cells by spatial locality, and enables us to only load the wind model for areas that can be seen from a users current view.  

Clients interact with the system through two main HTTP endpoints:

1) POST /covering?resolution=\<resolution> with a GeoJSON body, describing the area viewed by the client as an arbitrary polygon (which enables 3d views with a tilted camera). The response contains all S2 chunk IDs that are needed to cover the requested area, as well as the current sensor data from the reference sensor.
2) GET /data?cell=<s2_chunk_id>&resolution=\<resolution>&ws=<wind_speed_from_sensor>&wd=<wind_direction_from_sensor>, which returns the interpolated wind data for a given S2 chunk as a binary parquet file. 

While one could design the API differently, we chose to do it this way to enable easy and automatic client-side caching of S2 chunks by the browser, which improves performance when the view of a user shifts. 

One further optimization that we came up with is that we randomly hold back wind data for each client for up to 1 minute (eventual consistency from client perspective). By doing this, we avoid huge load peaks that would occur everytime the sensor data is updated, as then all chunks have to be interpolated again with the new sensor data and can't be pulled from the CDN or the client-side caches. Holding back the sensor data randomly for each client individually leads to a gradual recompuation of the chunks and an evenly distributed load over time. Through the API-design we still ensured that each client will have a consistent view (all chunks that a single client sees were rendered with the same sensor data), as well as monotonic reads consistency. 


The architecture diagram can be seen abovemar. 

My main contribution was the interpolation engine, which loads the wind model chunks from cloud storage, as well as the sensor data from Postgres, and then uses them to answer the interpolation requests by the clients. I also contributed some things for the generation of the POD models, as can be seen in the "pod" directory. 

Furthermore, I developed a benchmarking tool using "locust", which allows to simulate user behavior and perform load testing from a kubernetes cluster. 
During benchmarking, we found that our system can easily serve multiple 100s of concurrent users with 99th percentile latencies below 1s, with one user requiring about up to 1Mb/s of data (assuming the worst case where users request a new random view every second, which doesn't really enable client-side caching). It can probably scale further, but we didn't try since we were on a limited budget 




