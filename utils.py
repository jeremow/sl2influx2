from bs4 import BeautifulSoup as BS
from os import getcwd
# from config import BUFFER_DIR


def format_date_to_str(number, nb_digit):
    str_nb = str(number)
    if len(str_nb) == nb_digit or len(str_nb) > nb_digit:
        return str_nb
    elif len(str_nb) < nb_digit:
        return '0'+format_date_to_str(number, nb_digit-1)


def get_network_list(type_connection, network_list_values,
                     server_hostname=None, server_port=None, folder_file=None):

    if type_connection == 'server':
        if server_hostname is not None and server_port is not None:
            stations_xml = server_hostname + '.' + str(server_port) + '.xml'
        else:
            print('Server hostname/port not defined.')
            return None
    elif type_connection == 'folder':
        if folder_file is not None:
            stations_xml = folder_file
        else:
            print('Folder file not defined')
            return None
    else:
        print('type_connection not defined')
        return None
    try:
        print(getcwd())
        with open(f'config/{type_connection}/{stations_xml}', 'r') as fp:
            content = fp.read()
            config = BS(content, 'lxml-xml')

        for bs_network in config.find_all('Network'):
            network = bs_network.get('code')

            for bs_station in bs_network.find_all('Station'):
                station = bs_station.get('code')

                for bs_channel in bs_station.find_all('Channel'):
                    full_name = network + '.' + station + '.' + \
                                bs_channel.get('locationCode') + '.' + bs_channel.get('code')
                    print(full_name)
                    network_list_values.append(full_name)

        return 1

    except FileNotFoundError:
        print('Config file missing.')
        return -1
    except IndexError:
        print('Verify the config file, no station found')
        return -2


if __name__ == '__main__':
    network_list_values = []
    get_network_list('folder', [], network_list_values, folder_file='stations.xml')
    print(network_list_values)
