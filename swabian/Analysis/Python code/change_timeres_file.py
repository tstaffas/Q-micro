# NOTE: Uncompressed Binary 16 bytes (128bits). EXAMPLE BYTE STRINGS (entries):
"""
    # Positive & Positive
    b'\x00\x00\x00\x00     \x02 \x00\x00\x00     6\xf3\x1cNw        \x00\x00\x00'
    b'\x00\x00\x00\x00     \x01 \x00\x00\x00     \xb3\x9c\x1dNw     \x00\x00\x00'
    # Negative & Positive
    b'\x00\x00\x00\x00     \xff \xff\xff\xff    y\x1a\xb6`:         \x00\x00\x00'
    b'\x00\x00\x00\x00     \x02 \x00\x00\x00    G$\xc2`:            \x00\x00\x00'
"""

def manipulate_data(old_file, new_file, bad_ch):
    if old_file == new_file:
        print("\n*ERROR*\nProvided file names are the same:\n"
              f"   -->  {old_file}\n"
              "Please give two separate file names (old and new)")
        exit()

    # find out how many 16-byte entries there are in the 'input file'
    temp_file = open(old_file, "rb")
    temp_read = temp_file.read()        # read 16 bytes at a time
    temp_file.close()
    n_entries = int(len(temp_read)/16)

    # opening read/write data files:
    print("\nInitializing datafile manipulation\nUsing data file:", old_file)
    input_file = open(old_file, "rb")
    output_file = open(new_file, "wb")

    # loop through all the data entries, extracting and potentially fixing channel value
    for i in range(n_entries):

        # read 16 bytes at a time (size of each record by timetagger)
        binary_line = input_file.read(16)

        # read off current channel number (before any changes)
        channel_int = int.from_bytes(binary_line[4:8], 'little', signed=True)

        # If channel int is in undesired list --> change it. otherwise write unchanged bytes
        if channel_int in bad_ch:

            # Change channel number. Example: channel -1 --> 101
            int_new = abs(channel_int) + 100

            # Convert new channel number to bytestring (4bytes)
            bytes_new_ch = int_new.to_bytes(4, 'little', signed=True)

            # Write new file entry (with changed data)
            new_binary_line = binary_line[:4] + bytes_new_ch + binary_line[8:]
            output_file.write(new_binary_line)
        else:
            output_file.write(binary_line)

    # close files when done
    input_file.close()
    output_file.close()

    print("--> Done fixing data!")


# ---------------MAIN-----------------------
# TODO: maybe also have a list for new desired channel (replacement ch for each bad ch)

# note: active channels = { -1, 2 }
old_filename = 'Data/Testing_ch1_negative_pulse_ch2_positive_pulse.timeres'
new_filename = 'Data/Changed_Testing_ch1_negative_pulse_ch2_positive_pulse.timeres'
bad_channels = [-1, -2, -3, -4]  # note: any channels in this list will be changed
manipulate_data(old_filename, new_filename, bad_channels)

# note: active channels = { 1, 2, 3 }
#old_filename = 'Data/231030/ToF_terra_10MHz_det2_10.0ms_[2.1, 2.5, -3.2, -4.8]_100x100_231030.timeres'
##new_filename = 'Data/231030/Changed_ToF_terra_10MHz_det2_10.0ms_[2.1, 2.5, -3.2, -4.8]_100x100_231030.timeres'
#bad_channels = [-1, -2, -3, -4]  # note: any channels in this list will be changed
#manipulate_data(old_filename, new_filename, bad_channels)
# --------------------------------------
