# -*- coding: utf-8 -*-
# sl2influx2.py
# Author: Jeremy
# Description: Client Seedlink adapté à MONA + InfluxDB2

import argparse
import time

import obspy

from utils import get_network_list

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.domain.write_precision import WritePrecision
from influxdb_client.client.exceptions import InfluxDBError

from urllib3.exceptions import ReadTimeoutError

from obspy.clients.seedlink.client.seedlinkconnection import SeedLinkConnection
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy.clients.seedlink.seedlinkexception import SeedLinkException
from obspy.clients.seedlink.slpacket import SLPacket

# from config import *


class SeedLinkInfluxClient(EasySeedLinkClient):
    def __init__(self, server_sl_url, server_influx_url, bucket, token, org):
        self.network_list_values = []
        try:
            super(SeedLinkInfluxClient, self).__init__(server_sl_url, autoconnect=True)
            self.conn.timeout = 30
            self.connected = 0
            self.connected = get_network_list('server', self.network_list_values,
                                              server_hostname=self.server_hostname, server_port=self.server_port)
            if self.connected != 1:
                exit(1)

            self.streams = self.network_list_values
        except SeedLinkException:
            exit(1)

        self.server_influx = server_influx_url
        self.bucket = bucket
        self.token = token
        self.org = org
        self.client_influx = InfluxDBClient(url=self.server_influx, token=self.token, org=self.org)
        self.write_api = self.client_influx.write_api(SYNCHRONOUS)
        if self.client_influx.ping() is not True:
            print('Connection error to InfluxDB Database. Verify information.')
            exit(1)

    def on_data(self, tr):
        print(tr)

        # tr.resample(sampling_rate=25.0)
        t_start = obspy.UTCDateTime()

        if tr is not None and t_start - tr.stats.starttime <= 300:
            tr.detrend(type='constant')
            if tr.stats.location == '':
                station = tr.stats.network + '.' + tr.stats.station + '.' + tr.stats.channel
            else:
                station = tr.stats.network + '.' + tr.stats.station + '.' + tr.stats.location + '.' + tr.stats.channel

            data = []
            timestamp_start = int(tr.stats.starttime.timestamp * 1e3)
            for i, seismic_point in enumerate(tr.data):
                timestamp = timestamp_start + (i-1) * int(tr.stats.delta * 1e3)
                data.append({
                    "measurement": "SEISMIC_DATA",
                    "tags": {"location": station},
                    "fields": {
                        "trace": int(seismic_point),
                    },
                    "time": timestamp
                })
            try:
                self.write_api.write(self.bucket, self.org, record=data, write_precision=WritePrecision.MS)
                t_stop = obspy.UTCDateTime()
                print(f'{station} sent to {self.bucket} in {t_stop-t_start}s')
            except Exception as e:
                print(e)
                print(f'blockette of {station} not sent to {self.bucket}.')
                pass

        elif t_start - tr.stats.starttime > 300:
            print(f'blockette is too old ({(t_start - tr.stats.starttime)/60} min).')
        else:
            print("blockette contains no trace")

    def run(self):
        for station in self.streams:
            full_sta_name = station.split('.')
            net = full_sta_name[0]
            sta = full_sta_name[1]
            cha = full_sta_name[2] + full_sta_name[3]
            self.select_stream(net, sta, cha)
        while True:

            data = self.conn.collect()

            if data == SLPacket.SLTERMINATE:
                self.on_terminate()
                continue
            elif data == SLPacket.SLERROR:
                self.on_seedlink_error()
                continue

            # At this point the received data should be a SeedLink packet
            # XXX In SLClient there is a check for data == None, but I think
            #     there is no way that self.conn.collect() can ever return None
            assert(isinstance(data, SLPacket))

            packet_type = data.get_type()

            # Ignore in-stream INFO packets (not supported)
            if packet_type not in (SLPacket.TYPE_SLINF, SLPacket.TYPE_SLINFT):
                # The packet should be a data packet
                trace = data.get_trace()
                # Pass the trace to the on_data callback
                self.on_data(trace)


    def on_terminate(self):
        self._EasySeedLinkClient__streaming_started = False
        self.streams = self.conn.streams.copy()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.conn.multistation = True
        self.conn.streams = self.streams.copy()

        # self.conn.begin_time = UTCDateTime()

    def on_seedlink_error(self):
        self._EasySeedLinkClient__streaming_started = False
        self.streams = self.conn.streams.copy()
        del self.conn
        self.conn = SeedLinkConnection(timeout=30)
        self.conn.set_sl_address('%s:%d' %
                                 (self.server_hostname, self.server_port))
        self.conn.multistation = True
        self.conn.streams = self.streams.copy()

def get_arguments():
    """returns AttribDict with command line arguments"""
    parser = argparse.ArgumentParser(
        description='Launch a seedlink  and write the data into influxdb v2',
        formatter_class=argparse.RawTextHelpFormatter)

    # Script functionalities
    parser.add_argument('-s', '--server-sl', help='Path to SL server', required=True)
    parser.add_argument('-p', '--port-sl', help='Port of the SL server')
    parser.add_argument('-S', '--server-influx', help='Path of influx server', required=True)
    parser.add_argument('-P', '--port-influx', help='Port of influx server')
    parser.add_argument('-b', '--bucket', help='Name of the bucket', required=True)
    parser.add_argument('-o', '--org', help='Name of the organization', required=True)
    parser.add_argument('-t', '--token', help='Token authorization of influxdb', required=True)
    # parser.add_argument('-m', '--mseed', help='Path to mseed data folder', required=True)

    args = parser.parse_args()

    if args.port_sl is None:
        args.port_sl = '18000'
    if args.port_influx is None:
        args.port_influx = '8086'

    print(f'Server SL: {args.server_sl} ; Port: {args.port_sl}')
    print(f'Server Influx: {args.server_influx} ; Port: {args.port_influx}')
    print("--------------------------\n"
          "Starting Seedlink server and verifying Influx connection...")

    return args


if __name__ == '__main__':
    args = get_arguments()

    client = SeedLinkInfluxClient(args.server_sl + ':' + args.port_sl, args.server_influx + ':' + args.port_influx,
                                  args.bucket, args.token, args.org)

    client.run()
