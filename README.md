# Seedlink to InfluxDBv2
sl2influx2.py is a python script which query data from a Seedlink server and send it to a InfluxDB 2.x database.

## Installation
The best to do is to create a virtual environment with Python:
`python3 -m venv /path/to/new/virtual/environment`

Then you have to activate the environment. 

For Linux-based OS:
`source /path/to/new/virtual/environment/bin/activate`

For Windows:
`\path\to\new\virtual\environment\Scripts\activate`

Install the libraries with:
`pip install -r requirements.txt`

## Command
To launch the script, you open a terminal in the folder of sl2influx2.py. Be sure that your seedlink server is accessible and the bucket of influxDB 2.x you want to write in is WRTIE authorized with the Token.

Usage: `python sl2influx2.py [-h] -s SERVER_SL [-p PORT_SL] -S SERVER_INFLUX [-P PORT_INFLUX] -b BUCKET -o ORG -t TOKEN`

The following arguments are required: -s/--server-sl, -S/--server-influx, -b/--bucket, -o/--org, -t/--token. Default ports are respectively 18000 and 8086.
You need to create a config file in the directory `config/server/name.server.port.server.xml` with the stations you want to read from the seedlink server. This config file has to be formatted in the stationXML standard (information on FDSN). An example is given on this repo for `rtserver.ipgp.fr` on port `18000`. 

## Information

The data will be stored in the InfluxDB bucket precised in the command-line. The structure built ìn the bucket is `_measurement='SEISMIC_DATA'` ; `_field='trace'` ; `location='NET.STA.LOC.CHA'`.

In Flux language, to display the data of the station F.FDFM.00.BHZ with a window of 25ms

```
from(bucket: "rtserver-seismic")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "SEISMIC_DATA")
  |> filter(fn: (r) => r["_field"] == "trace")
  |> filter(fn: (r) => r["location"] == "G.FDFM.00.BHZ")
  |> aggregateWindow(every: 25ms, fn: mean, createEmpty: true)
  |> yield(name: "mean")
```
