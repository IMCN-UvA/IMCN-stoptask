
from StopSignal import *
from psychopy import core

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass

try:
    # Kill Finder during execution (this will be fun)
    applescript="\'tell application \"Finder\" to quit\'"
    shellCmd = 'osascript -e '+ applescript
    os.system(shellCmd)
except:
    pass

# Set nice to -20: extremely high PID priority
new_nice = -20
sysErr = os.system("sudo renice -n %s %s" % (new_nice, os.getpid()))
if sysErr:
    print('Warning: Failed to renice, probably you arent authorized as superuser')



def main():
    # Load config
    from exptools.utils.config import ExpToolsConfig
    config = ExpToolsConfig()

    # Set-up monitor on the fly
    from psychopy import monitors
    my_monitor = monitors.Monitor(name=config.get('screen', 'monitor_name'))
    my_monitor.setSizePix(config.get('screen', 'size'))
    my_monitor.setWidth(config.get('screen', 'physical_screen_size')[0])
    my_monitor.setDistance(config.get('screen', 'physical_screen_distance'))
    my_monitor.saveMon()


    initials = raw_input('Your initials/subject number: ')
    session_num = int(raw_input('Session number: '))

    scanner = ''
    simulate = ''
    while scanner not in ['y', 'n']:
        scanner = raw_input('Are you in the scanner (y/n)?: ')
        if scanner not in ['y', 'n']:
            print('I don''t understand that. Please enter ''y'' or ''n''.')

    if scanner == 'n':
        while simulate not in ['y', 'n']:
            simulate = raw_input('Do you want to simulate scan pulses? This is useful during behavioral pilots '
                                 '(y/n): ')
            if simulate not in ['y', 'n']:
                print('I don''t understand that. Please enter ''y'' or ''n''.')

    sess = StopSignalSession(subject_initials=initials, index_number=session_num, tr=2, config=config)

    if simulate == 'y':
        # Run with simulated scanner (useful for behavioral pilots with eye-tracking)
        from psychopy.hardware.emulator import launchScan
        scanner_emulator = launchScan(win=sess.screen, settings={'TR': 2, 'volumes': 30000, 'sync': 't'}, mode='Test')
    sess.run()


if __name__ == '__main__':
    main()

    # Force python to quit (so scanner emulator also stops)
    core.quit()




#
#
# # Set-up session
# sess = StopSignalSession('DEBUG',
#                          1,
#                          run=1,
#                          tr=3,
#                          config=config)
#
# # EMULATOR
# from psychopy.hardware.emulator import launchScan
# scanner_emulator = launchScan(win=sess.screen, settings={'TR': 2, 'volumes': 30000, 'sync': 't'}, mode='Test')
#
# # run
# sess.run()
#
# # Load & dump data
# import cPickle as pkl
# from pprint import pprint
#
# with open(sess.output_file + '_outputDict.pkl', 'r') as f:
#     a = pkl.load(f)
# pprint(a)
#
# core.quit()