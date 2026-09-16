import runpy

runpy.run_path('android-r3/r59_full_modern_parity_payload.py', run_name='__main__')
runpy.run_path('android-r3/r59_test_compat_patch.py', run_name='__main__')

print('R59 full modern parity patch + inherited test compatibility applied')
