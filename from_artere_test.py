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


def from_artere(datfile):
    with open(datfile) as artereFile:
        content = artereFile.readlines()
        for record in content:
            record = record.split()
            recordType = record[0]
            if recordType == 'SLACK':
                global slackBus
                slackBus = record[1]
            elif recordType == 'FNOM':
                global frequency
                frequency = float(record[1])
            else:
                frequency = 50


    with open(datfile) as artereFile:
        content = artereFile.readlines()
        for record in content:
            record = record.split()
            recordType = record[0]


            if recordType  == "BUS":
                create_bus(record)
            elif recordType == "LINE":
                create_line(record)
            elif recordType == "TRANSFO":
                create_transformer_from_TRANSFO(record)
            elif recordType == "TRFO":
                create_transformer_from_TRFO(record)
            elif recordType == "GENER":
                create_generator(record)
            elif recordType == "SWITCH":
                create_switch(record)
            elif recordType == "LFRESV":
                create_LFRESV(record)


    createNewFile(datfile)


def create_bus(record):
    bus_name = record[1]
    vn_kv = float(record[2])
    Pload = float(record[3])
    Qload = float(record[4])
    Bshunt = float(record[5])
    Qshunt = float(record[6])

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
    if Pload > 0 or Pload <0 or Qload > 0 or Qload < 0:
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



def create_LFRESV(record):
    init_vm_pu = float(record[2])  # Voltage magnitude in pu  # MODULE
    init_va_degree = float(record[3])  # Phase angle in radians   # PHASE

    init_vm_pu_list.append(init_vm_pu)
    init_va_degree_list.append(init_va_degree)

def create_switch(record):
    switch_name = record[1]
    first_bus = record[2]
    second_bus = record[3]
    status = int(record[4])

    status = checkStatus(status)

    created_switch = f'pp.create_switch(net, bus={busDict[first_bus]["name"]}, name="{switch_name}" ,element={second_bus}, et="b" ,closed={status})\n'
    switchList.append(created_switch)


def create_generator(record):
    gener_name = record[1]
    bus_connected = record[2]
    Pproduction = float(record[4])
    Qproduction = float(record[5])
    Snom = record[7]
    VIMP = record[6]
    Qmin = float(record[8])
    Qmax = float(record[9])
    On_off = int(record[10])

    # Check if it is in service
    in_service = checkStatus(On_off)

    # if VIMP is zero, the generator is treated as a PQ bus (we create sgen)
    # Otherwise it is treated as a PV bus and the Q is ignored
    if VIMP == "0":
        created_sgen = f'pp.create_sgen(net, bus={busDict[bus_connected]["name"]}, p_mw={Pproduction}, ' \
                       f'q_mvar={Qproduction}, sn_mva={Snom}, name="{gener_name}", max_q_mvar={Qmax}, min_q_mvar={Qmin}, in_service={in_service})\n'
        generatorList.append(created_sgen)

    else:
        if gener_name == slackBus:
            created_gen = f'pp.create_gen(net, p_mw={Pproduction}, max_q_mvar={Qmax}, min_q_mvar={Qmin}, sn_mva={Snom}, ' \
                          f'bus={busDict[bus_connected]["name"]}, vm_pu={VIMP}, name="{gener_name}", slack={True}, in_service={in_service})\n'
            generatorList.append(created_gen)

        elif gener_name == "Ext_Grid":
            created_gen = f'pp.create_gen(net, p_mw={Pproduction}, max_q_mvar={Qmax}, min_q_mvar={Qmin}, sn_mva={Snom}, ' \
                          f'bus={busDict[bus_connected]["name"]}, vm_pu={VIMP}, name="{gener_name}", slack={True}, in_service={in_service})\n'
            generatorList.append(created_gen)

        else:
            created_gen = f'pp.create_gen(net, p_mw={Pproduction}, max_q_mvar={Qmax}, min_q_mvar={Qmin}, sn_mva={Snom}, ' \
                          f'bus={busDict[bus_connected]["name"]}, vm_pu={VIMP}, name="{gener_name}", slack={False}, in_service={in_service})\n'
            generatorList.append(created_gen)


def create_transformer_from_TRFO(record):
    transfo_name = record[1]
    from_bus = record[2]
    to_bus = record[3]
    con_bus = record[4]
    resistance = (record[5])

    if con_bus == '\'' and resistance == '\'':
        con_bus = None
        resistance = float(record[6])
        x_reactance = float(record[6 + 1])
        susceptance = float(record[7 + 1])
        Nratio = float(record[8 + 1])
        snom = float(record[9 + 1])
        N_First = float(record[10 + 1]) * 100
        N_Last = float(record[11 + 1]) * 100
        NBPOS = int(float(record[12 + 1]))
        #TOLV = record[13 + 1]
        #VDES = record[14 + 1]
        On_off = int(record[15 + 1])
    else:
        resistance = float(record[5])
        x_reactance = float(record[6])
        susceptance = float(record[7])
        Nratio = float(record[8])
        snom = float(record[9])
        N_First = float(record[10])
        N_Last = float(record[11])
        NBPOS = int(float(record[12]))
        #TOLV = record[13]
        #VDES = record[14]
        On_off = int(record[15])

    in_service = checkStatus(On_off)
    # to_bus = check_for_int_bus(to_bus)
    # from_bus = check_for_int_bus(from_bus)

    # vkr, vk, i0 percent
    Ym = susceptance
    rk = resistance
    xk = x_reactance
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
        if con_bus.isdigit():
            con_bus = "b" + con_bus
    except:
        pass

    try:
        if busDict[con_bus]['voltage'] == busDict[high_lvl_bus]['voltage']:
            tap_side = "\"hv\""
        elif busDict[con_bus]['voltage'] == busDict[low_lvl_bus]['voltage']:
            tap_side = "\"lv\""
        else:
            tap_side = None
    except:
        tap_side = None

    # tap_max = NBPOS, tap_min=0
    # check if the N ratio is not 100, while NBPOS, N_first and N_Last are 0.
    if Nratio != 100 and NBPOS == 0 and N_First == 0 and N_Last == 0:
        if Nratio > 100:
            tap_neutral = 0
            tap_min = Nratio - 100
            tap_max = Nratio - 100
            tap_pos = Nratio - 100
            tap_step_percent = 1
            tap_side = "\"hv\""

        elif Nratio < 100:
            tap_neutral = 0
            tap_min = -100 + Nratio
            tap_max = -100 + Nratio
            tap_pos = -100 + Nratio
            tap_step_percent = 1
            tap_side = "\"lv\""

        # Create a string
        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={snom}, name="{transfo_name}", ' \
                              f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, ' \
                              f'tap_pos={tap_pos}, tap_neutral={tap_neutral}, tap_step_percent={tap_step_percent}, tap_side={tap_side}, tap_min={tap_min}, tap_max={tap_max}, in_service={in_service})\n'

        transformersList.append(created_transformer)

    # if Nratio , N_First, N_last are equal:
    elif Nratio != 100 and N_First == N_Last and N_Last == Nratio:
        if Nratio > 100:
            tap_neutral = 0
            tap_min = Nratio - 100
            tap_max = Nratio - 100
            tap_pos = Nratio - 100
            tap_step_percent = 1
            # tap_side = "\"hv\""

        elif Nratio < 100:
            tap_neutral = 0
            tap_min = -100 + Nratio
            tap_max = -100 + Nratio
            tap_pos = -100 + Nratio
            tap_step_percent = 1
            # tap_side = "\"lv\""

        # Create a string
        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={snom}, name="{transfo_name}", ' \
                              f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, ' \
                              f'tap_pos={tap_pos}, tap_neutral={tap_neutral}, tap_step_percent={tap_step_percent}, tap_side={tap_side}, tap_min={tap_min}, tap_max={tap_max}, in_service={in_service})\n'

        # Store the string to a list
        transformersList.append(created_transformer)

    elif Nratio == 100 and N_First == 0 and N_Last == 0:
        # Create a string
        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={snom}, name="{transfo_name}", ' \
                              f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, ' \
                              f'i0_percent={i0_percent}, in_service={in_service})\n'

        # Store the string to a list
        transformersList.append(created_transformer)

    elif Nratio > 0 and N_First > 0 and N_Last > 0 and NBPOS > 0:

        tap_step_percent = (N_Last - N_First) / (NBPOS - 1)

        tap_neutral = (100 - float(N_First)) / tap_step_percent
        tap_neutral = round(tap_neutral)

        tap_pos = (float(Nratio) - N_First) / tap_step_percent
        tap_pos = round(tap_pos)

        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={snom}, name="{transfo_name}", ' \
                              f'vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, ' \
                              f'tap_pos={tap_pos}, tap_neutral={tap_neutral}, tap_step_percent={tap_step_percent}, tap_side={tap_side}, tap_min=0, tap_max={NBPOS - 1}, in_service={in_service})\n'

        transformersList.append(created_transformer)


def create_transformer_from_TRANSFO(record):
    transfo_name = record[1]
    from_bus = record[2]
    to_bus = record[3]
    resistance = float(record[4])
    x_reactance = float(record[5])
    susceptanceB1 = float(record[6])
    susceptanceB2 = float(record[7])
    N_ratio = float(record[8])
    susceptance = (susceptanceB1 + susceptanceB2) / 2.0
    snom = float(record[10])
    status = int(record[11])
    PHI = float(record[9])

    # to_bus = check_for_int_bus(to_bus)
    # from_bus = check_for_int_bus(from_bus)
    status = checkStatus(status)

    # vk, vkr, i0_percent
    ym = susceptance
    rk = resistance
    xk = x_reactance
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
        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={snom}, ' \
                              f'name={transfo_name}, shift_degree={PHI}, vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent}, pfe_kw=0, i0_percent={i0_percent}, status={status})\n'
    else:
        created_transformer = f'pp.create_transformer_from_parameters(net, hv_bus={busDict[high_lvl_bus]["name"]}, lv_bus={busDict[low_lvl_bus]["name"]}, sn_mva={snom}, name={transfo_name}, ' \
                              f'shift_degree={PHI}, vn_hv_kv={busDict[high_lvl_bus]["voltage"]}, vn_lv_kv={busDict[low_lvl_bus]["voltage"]}, vkr_percent={vkr_percent}, vk_percent={vk_percent},' \
                              f' pfe_kw=0, i0_percent={i0_percent}, tap_min={tap_min}, tap_max={tap_max}, tap_step_percent={tap_step_percent}, tap_pos={tap_pos},tap_neutral={tap_neutral}, tap_side={tap_side}, status={status})\n'

    transformersList.append(created_transformer)



def create_line(record):
    line_name = record[1]
    from_bus = record[2]
    to_bus = record[3]
    R_Ohm = float(record[4])
    X_Ohm = float(record[5])
    half_shunt_suceptance = float(record[6]) / 10 ** 6  # It is given in μS
    Snom = float(record[7])
    status = int(record[8])

    in_service = checkStatus(status)


    # Calculate the maximum curent
    line_voltage = busDict[from_bus]["voltage"]
    Imax = (Snom * 10 ** 6) / (math.sqrt(3) * line_voltage * 10 ** 3)
    Imax = Imax / 1000
    Imax = format(Imax, '.6f')

    # Calculate the capacitance in nF.  ωC/2
    capacitance = (half_shunt_suceptance * 2) / 2 * math.pi * frequency
    capacitance = capacitance * 10 ** 9  # nF
    capacitance = format(capacitance, '.5f')

    created_line = f'pp.create_line_from_parameters(net, from_bus={busDict[from_bus]["name"]}, to_bus={busDict[to_bus]["name"]}, name="{line_name}"' \
                   f', length_km=1, r_ohm_per_km={R_Ohm}, x_ohm_per_km={X_Ohm}, max_i_ka={Imax}, c_nf_per_km={capacitance}, in_service={in_service})\n'
    linesList.append(created_line)


def checkStatus(element_status):
    if element_status == 1:
        return True
    return False


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
