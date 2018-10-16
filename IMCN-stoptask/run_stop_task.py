
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
    import glob
    import datetime
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
    if initials == 'pilot' or initials == 'practice':
        session_tr = 2
    else:
        session_tr = int(raw_input('Session TR: '))

    if initials == 'practice':
        start_block = 1
        simulate = 'y'
    else:
        start_block = int(raw_input('At which block do you want to start? NB: 1 is the first block! '))
        if start_block > 1:
            # check if previous stairs exist
            now = datetime.datetime.now()
            opfn = now.strftime("%Y-%m-%d")
            expected_filename = initials + '_' + str(session_tr) + '_' + opfn
            fns = glob.glob('./data/' + expected_filename + '_*_staircases.pkl')
            fns.sort()
            if len(fns) == 0:
                raw_input('Could not find previous stairs for this subject today... Enter any key to verify you want '
                          'to make new staircases. ')
            elif len(fns) == 1:
                print('Found previous staircase file: %s' % fns[0])
            elif len(fns) > 1:
                print('Found multiple staircase files. Please remove the unwanted ones, otherwise I cannot run.')
                print(fns)
                core.quit()

        scanner = ''
        simulate = ''
        while scanner not in ['y', 'n']:
            scanner = raw_input('Are you in the scanner (y/n)?: ')
            if scanner not in ['y', 'n']:
                print('I don''t understand that. Please enter ''y'' or ''n''.')

        if scanner == 'n':
            while simulate not in ['y', 'n']:
                simulate = raw_input('Do you want to simulate scan pulses? This is useful during behavioral pilots (y/n): ')
                if simulate not in ['y', 'n']:
                    print('I don''t understand that. Please enter ''y'' or ''n''.')

    sess = StopSignalSession(subject_initials=initials, index_number=session_tr, tr=session_tr, start_block=start_block,
                             config=config)

    if simulate == 'y':
        # Run with simulated scanner (useful for behavioral pilots with eye-tracking)
        from psychopy.hardware.emulator import launchScan
        scanner_emulator = launchScan(win=sess.screen, settings={'TR': session_tr, 'volumes': 30000, 'sync': 't'},
                                      mode='Test')
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