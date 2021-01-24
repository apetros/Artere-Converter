"""
The aim of this program is to convert a .dat file which is used for the ARTERE program.
This program reads and grabs the data from the .dat file and creates a Python file in order
to make a network with pandapower.
"""
import math
busList = []
init_vm_pu_list = []
init_va_degree_list = []
load_list = []
generatorList = []
transformersList = []
linesList = []
switchList = []
shuntsList = []
busDict = {}
bus_voltage_dict = {}
genDict = {}


def check_for_int_bus(bus_name):
    # This function checks if a bus is consisted only from numbers
    try:
        bus_name = int(bus_name)
    except:
        pass
    if type(bus_name) == int:
        bus_name = str(bus_name)
        bus_name = "b" + bus_name
    return bus_name


def checkStatus(element_status):
    in_service = ""
    if element_status == 1:
        in_service = True
    elif element_status == 0:
        in_service = False
    return in_service


def from_artere(artereFile):
    # Search for the slack bus
    with open(artereFile) as Artere_file:
        Lines = Artere_file.readlines()
        for Line in Lines:
            line = Line.split()
            if len(line) > 0:
                if line[0] == 'SLACK':
                    slack_bus = line[1]
                global frequency
                if line[0] == 'FNOM':
                    frequency = float(line[1])
                else:
                    frequency = 50
                omega = math.pi * 2 * frequency


    with open(artereFile) as Artere_file:
        # Read the file as one unique string
        content = Artere_file.read()
        # Split the string to a list of strings.
        Lines = content.split(';')
        # Read the file line by line and grap data
        for Line in Lines:
            # Split every line to a list
            line = Line.split()

            if len(line) > 0:
                # If the first work is BUS, we grab its data
                if line[0] == 'BUS':
                    bus_name = (line[1])
                    bus_name = check_for_int_bus(bus_name)
                    vn_kv = float(line[2])
                    Pload = float(line[3])
                    Qload = float(line[4])
                    Bshunt = float(line[5])
                    Qshunt = float(line[6])


                    # List of bus names
                    try:
                        bus_name = bus_name.replace(" ", "_")
                    except:
                        pass

                    # Create a bus
                    busDict[bus_name] = {}
                    busDict[bus_name]["name"] = bus_name
                    busDict[bus_name]["voltage"] = vn_kv

                    # Create a string that is going to be stored in the Python file.
                    created_bus = f"{bus_name} = pp.create_bus(net, vn_kv={vn_kv}, name=\"{bus_name}\", in_service=True)\n"
                    busList.append(created_bus)

                    # If the bus has a load, create a load connected to the bus.
                    if Pload > 0 or Qload > 0:
                        created_load = f"pp.create_load(net, bus={bus_name}, p_mw={Pload}, q_mvar={Qload}, name=\"{bus_name}\", in_service=True)\n"
                        load_list.append(created_load)

                    # if the bus has a shunt, create a shunt to the bus
                    # Qshunt-> Create load, Bshunt-> Create shunt
                    if Qshunt != 0:
                        created_load = f"pp.create_load(net, bus={bus_name}, name=\"{bus_name}_Shunt\", p_mw=0, q_mvar={Qshunt}, in_service=True) \n"
                        load_list.append(created_load)
                    if Bshunt != 0:
                        created_shunt = f"pp.create_shunt(net, bus={bus_name}, q_mvar={Bshunt}, in_service=True)\n"
                        shuntsList.append(created_shunt)

                # Transmittion lines
                if line[0] == 'LINE':
                    line_name = line[1]
                    from_bus = line[2]
                    to_bus = line[3]
                    R_Ohm = float(line[4])
                    X_Ohm = float(line[5])
                    half_shunt_suceptance = float(line[6]) / 10 ** 6  # It is given in μS
                    Snom = float(line[7])
                    On_off = int(line[8])

                    in_service = checkStatus(On_off)

                    from_bus = check_for_int_bus(from_bus)
                    to_bus = check_for_int_bus(to_bus)

                    # Calculate the maximum curent
                    line_voltage = busDict[from_bus]["voltage"]
                    Imax = (Snom * 10 ** 6) / (math.sqrt(3) * line_voltage * 10 ** 3)
                    Imax = Imax / 1000
                    Imax = format(Imax, '.6f')

                    # Calculate the capacitance in nF.  ωC/2
                    Capacitance = (half_shunt_suceptance * 2) / (omega)
                    Capacitance = Capacitance * 10 ** 9     # nF
                    Capacitance = format(Capacitance, '.5f')

                    created_line = f'pp.create_line_from_parameters(net, from_bus={busDict[from_bus]["name"]}, to_bus={busDict[to_bus]["name"]}, name="{line_name}"' \
                                   f', length_km=1, r_ohm_per_km={R_Ohm}, x_ohm_per_km={X_Ohm}, max_i_ka={Imax}, c_nf_per_km={Capacitance}, in_service={in_service})\n'
                    linesList.append(created_line)

                # LTC-V
                if line[0] == 'LTC-V':
                    print('LTC-V is not supported. ')
                    raise Warning('LTC-V is not supported.')

                # Transformers for TRANSFO record
                if line[0] == 'TRANSFO':
                    transfo_name = line[1]
                    from_bus = line[2]
                    to_bus = line[3]
                    Resistance = float(line[4])
                    Xreactance = float(line[5])
                    SusceptanceB1 = float(line[6])
                    SusceptanceB2 = float(line[7])
                    N_ratio = float(line[8])
                    Susceptance = (SusceptanceB1 + SusceptanceB2) / 2.0
                    Snom = float(line[10])
                    On_off = int(line[11])
                    PHI = float(line[9])

                    to_bus = check_for_int_bus(to_bus)
                    from_bus = check_for_int_bus(from_bus)
                    in_service = checkStatus(On_off)

                    # vk, vkr, i0_percent
                    ym = Susceptance
                    rk = Resistance
                    xk = Xreactance
                    zk = math.sqrt(pow(rk, 2) + pow(xk, 2))
                    vk_percent = zk
                    vkr_percent = rk
                    i0_percent = ym

                    # Check which bus is High level and which is low.
                    if busDict[from_bus]['voltage'] > busDict[to_bus]['voltage']:
                        high_lvl_bus = from_bus
                        low_lvl_bus = to_bus
                    else:
                        high_lvl_bus = to_bus
                        low_lvl_bus = from_bus

                    if N_ratio > 100:
                        tap_neutral = 0
                        tap_min = N_ratio - 100
                        tap_max = N_ratio - 100
                        tap_pos = N_ratio - 100
                        tap_step_percent = 1
                        tap_side = "\"hv\""

                    elif N_ratio < 100:
                        tap_neutral = 0
                        tap_min = -100 + N_ratio
                        tap_max = -100 + N_ratio
                        tap_pos = -100 + N_ratio
                        tap_step_percent = 1
                        tap_side = "\"hv\""

                    # Create a transformer
                    # if the ratio is not 100, we should take into account the taps.
                    if N_ratio == 100:
                        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={Snom}, ' \
                                              f'name={transfo_name}, shift_degree={PHI}, vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, in_service={in_service})\n'
                    else:
                        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={Snom}, name={transfo_name}, ' \
                                              f'shift_degree={PHI}, vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent},' \
                                              f' pfe_kw=0, i0_percent={i0_percent}, tap_min={tap_min}, tap_max={tap_max}, tap_step_percent={tap_step_percent}, tap_pos={tap_pos},tap_neutral={tap_neutral}, tap_side={tap_side}, in_service={in_service})\n'

                    transformersList.append(created_transformer)

                # Transformer for TRFO record
                if line[0] == 'TRFO':
                    transfo_name = line[1]
                    from_bus = line[2]
                    to_bus = line[3]
                    CON_BUS = line[4]
                    Ohm_Resistance = (line[5])


                    if CON_BUS == '\'' and Ohm_Resistance == '\'':
                        CON_BUS = None
                        Ohm_Resistance = float(line[6])
                        Xreactance = float(line[6 + 1])
                        Susceptance = float(line[7 + 1])
                        N_ratio = float(line[8 + 1])
                        Snom = float(line[9 + 1])
                        N_First = float(line[10 + 1]) * 100
                        N_Last = float(line[11 + 1]) * 100
                        NBPOS = int(float(line[12 + 1]))
                        TOLV = line[13 + 1]
                        VDES = line[14 + 1]
                        On_off = int(line[15 + 1])
                    else:
                        Ohm_Resistance = float(line[5])
                        Xreactance = float(line[6])
                        Susceptance = float(line[7])
                        N_ratio = float(line[8])
                        Snom = float(line[9])
                        N_First = float(line[10])
                        N_Last = float(line[11])
                        NBPOS = int(float(line[12]))
                        TOLV = line[13]
                        VDES = line[14]
                        On_off = int(line[15])

                    in_service = checkStatus(On_off)
                    to_bus = check_for_int_bus(to_bus)
                    from_bus = check_for_int_bus(from_bus)

                    # vkr, vk, i0 percent
                    Ym = Susceptance
                    rk = Ohm_Resistance
                    xk = Xreactance
                    zk = math.sqrt(pow(rk, 2) + pow(xk, 2))
                    vk_percent = zk
                    vkr_percent = rk
                    i0_percent = Ym

                    # Check which bus is High level and which is low.
                    if busDict[from_bus]["voltage"] > busDict[to_bus]["voltage"]:
                        high_lvl_bus = from_bus
                        low_lvl_bus = to_bus
                    else:
                        high_lvl_bus = to_bus
                        low_lvl_bus = from_bus


                    # TAPS
                    try:
                        if CON_BUS.isdigit():
                            CON_BUS = "b" + CON_BUS
                    except:
                        pass

                    try:
                        if busDict[CON_BUS]['voltage'] == busDict[high_lvl_bus]['voltage']:
                            tap_side = "\"hv\""
                        elif busDict[CON_BUS]['voltage'] == busDict[low_lvl_bus]['voltage']:
                            tap_side = "\"lv\""
                        else:
                            tap_side = None
                    except:
                        tap_side = None

                    # tap_max = NBPOS, tap_min=0
                    # check if the N ratio is not 100, while NBPOS, N_first and N_Last are 0.
                    if N_ratio != 100 and NBPOS == 0 and N_First == 0 and N_Last == 0:
                        if N_ratio > 100:
                            tap_neutral = 0
                            tap_min = N_ratio - 100
                            tap_max = N_ratio - 100
                            tap_pos = N_ratio - 100
                            tap_step_percent = 1
                            tap_side = "\"hv\""

                        elif N_ratio < 100:
                            tap_neutral = 0
                            tap_min = -100 + N_ratio
                            tap_max = -100 + N_ratio
                            tap_pos = -100 + N_ratio
                            tap_step_percent = 1
                            tap_side = "\"lv\""

                        # Create a string
                        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={Snom}, name="{transfo_name}", ' \
                                              f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, ' \
                                              f'tap_pos={tap_pos}, tap_neutral={tap_neutral}, tap_step_percent={tap_step_percent}, tap_side={tap_side}, tap_min={tap_min}, tap_max={tap_max}, in_service={in_service})\n'

                        transformersList.append(created_transformer)

                    # if N_ratio , N_First, N_last are equal:
                    elif N_ratio != 100 and N_First == N_Last and N_Last == N_ratio:
                        if N_ratio > 100:
                            tap_neutral = 0
                            tap_min = N_ratio - 100
                            tap_max = N_ratio - 100
                            tap_pos = N_ratio - 100
                            tap_step_percent = 1
                            #tap_side = "\"hv\""

                        elif N_ratio < 100:
                            tap_neutral = 0
                            tap_min = -100 + N_ratio
                            tap_max = -100 + N_ratio
                            tap_pos = -100 + N_ratio
                            tap_step_percent = 1
                            #tap_side = "\"lv\""

                        # Create a string
                        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={Snom}, name="{transfo_name}", ' \
                                                  f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, ' \
                                                  f'tap_pos={tap_pos}, tap_neutral={tap_neutral}, tap_step_percent={tap_step_percent}, tap_side={tap_side}, tap_min={tap_min}, tap_max={tap_max}, in_service={in_service})\n'

                        # Store the string to a list
                        transformersList.append(created_transformer)

                    elif N_ratio == 100 and N_First == 0 and N_Last == 0:
                        # Create a string
                        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={Snom}, name="{transfo_name}", ' \
                                              f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, ' \
                                              f'i0_percent={i0_percent}, in_service={in_service})\n'

                        # Store the string to a list
                        transformersList.append(created_transformer)

                    elif N_ratio > 0 and N_First > 0 and N_Last > 0 and NBPOS > 0:

                        tap_step_percent = (N_Last - N_First) / (NBPOS - 1)

                        tap_neutral = (100 - float(N_First)) / tap_step_percent
                        tap_neutral = round(tap_neutral)

                        tap_pos = (float(N_ratio) - N_First) / tap_step_percent
                        tap_pos = round(tap_pos)

                        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={Snom}, name="{transfo_name}", ' \
                                                  f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, ' \
                                                  f'tap_pos={tap_pos}, tap_neutral={tap_neutral}, tap_step_percent={tap_step_percent}, tap_side={tap_side}, tap_min=0, tap_max={NBPOS-1}, in_service={in_service})\n'

                        transformersList.append(created_transformer)

                # Generators
                if line[0] == 'GENER':
                    gener_name = line[1]
                    bus_connected = line[2]
                    Pproduction = float(line[4])
                    Qproduction = float(line[5])
                    Snom = line[7]
                    VIMP = line[6]
                    Qmin = float(line[8])
                    Qmax = float(line[9])
                    On_off = int(line[10])

                    # Check if it is in service
                    in_service = checkStatus(On_off)

                    # if VIMP is zero, the generator is treated as a PQ bus (we create sgen)
                    # Otherwise it is treated as a PV bus and the Q is ignored
                    if VIMP == "0":
                        created_sgen = f'pp.create_sgen(net, bus={busDict[bus_connected]["name"]}, p_mw={Pproduction}, q_mvar={Qproduction}, sn_mva={Snom}, name="{gener_name}", max_q_mvar={Qmax}, min_q_mvar={Qmin}, in_service={in_service})\n'
                        generatorList.append(created_sgen)

                    else:
                        if gener_name == slack_bus:
                            created_gen = f'pp.create_gen(net, p_mw={Pproduction}, max_q_mvar={Qmax}, min_q_mvar={Qmin}, sn_mva={Snom}, bus={busDict[bus_connected]["name"]}, vm_pu={VIMP}, name="{gener_name}", slack={True}, in_service={in_service})\n'
                            generatorList.append(created_gen)

                        elif gener_name == "Ext_Grid":
                            created_gen = f'pp.create_gen(net, p_mw={Pproduction}, max_q_mvar={Qmax}, min_q_mvar={Qmin}, sn_mva={Snom}, bus={busDict[bus_connected]["name"]}, vm_pu={VIMP}, name="{gener_name}", slack={True}, in_service={in_service})\n'
                            generatorList.append(created_gen)

                        else:
                            created_gen = f'pp.create_gen(net, p_mw={Pproduction}, max_q_mvar={Qmax}, min_q_mvar={Qmin}, sn_mva={Snom}, bus={busDict[bus_connected]["name"]}, vm_pu={VIMP}, name="{gener_name}", slack={False}, in_service={in_service})\n'
                            generatorList.append(created_gen)

                # Switches
                if line[0] == 'SWITCH':
                    switch_name = line[1]
                    first_bus = line[2]
                    second_bus = line[3]
                    On_off = int(line[4])

                    in_service = checkStatus(On_off)

                    created_switch = f'pp.create_switch(net, bus={busDict[first_bus]["name"]}, name="{switch_name}" ,element={second_bus}, et="b" ,closed={in_service})\n'
                    switchList.append(created_switch)

                # LFRESV specifies the voltage magnitude and phase at a bus.
                if line[0] == 'LFRESV':
                    init_vm_pu = float(line[2])  # Voltage magnitude in pu  # MODULE
                    init_va_degree = float(line[3])  # Phase angle in radians   # PHASE

                    init_vm_pu_list.append(init_vm_pu)
                    init_va_degree_list.append(init_va_degree)

    createNewFile(artereFile)



def createNewFile(file):
    # Those lines get the removes the .dat extension and puts .py
    newPythonFile = file.split('.')[0] + ".py"

    # Here we create the Python file. It will contain all the elements and it will run the powerflow
    with open(newPythonFile, 'w') as pythonFile:
        pythonFile.write(f"""import pandapower as pp

# Create an empty network 
net = pp.create_empty_network(f_hz={frequency}, sn_mva={100})
    
    """)
        pythonFile.write('\n# list of Buses:\n')
        for bus in busList:
            pythonFile.write(bus)

        pythonFile.write('\n\n# list of Loads:\n')
        for load in load_list:
            pythonFile.write(load)

        pythonFile.write('\n\n# List of Shunts:\n')
        for shunt in shuntsList:
            pythonFile.write(shunt)

        pythonFile.write('\n\n# list of Lines:\n')
        for line in linesList:
            pythonFile.write(line)

        pythonFile.write('\n\n# list of Transformers:\n')
        for transformer in transformersList:
            pythonFile.write(transformer)

        pythonFile.write('\n\n# list of Generators:\n')
        for generator in generatorList:
            pythonFile.write(generator)

        pythonFile.write('\n\n# List of Switches:\n')
        for switch in switchList:
            pythonFile.write(switch)

        pythonFile.write(f"""
    
# Display all the elements
print('Buses: ')
print(net.bus)
    
    
print('Loads:')
print(net.load) 
    
print('Shunts')
print(net.shunt)
    
    
print('lines:')
print(net.line)
    
    
print('Transformers: ')
print(net.trafo)
    
    
print('Generators: ')
print(net.gen)
    
    
print('Switchers:')
print(net.switch)
    
init_va_degree_list = {init_va_degree_list} 
init_vm_pu_list = {init_vm_pu_list}
    
    
# Run power flow
if len(init_va_degree_list) > 0 and len(init_vm_pu_list) > 0:
    pp.runpp(net, init_va_degree=init_va_degree_list, init_vm_pu=init_vm_pu_list)
else:
    pp.runpp(net)
    
print('bus info')
    
print(net.res_bus)          # bus results
    
print('load info')
    
print(net.res_load)
""")

