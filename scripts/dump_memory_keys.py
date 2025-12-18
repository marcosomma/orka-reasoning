import redis
r=redis.from_url('redis://localhost:6380/0')
keys=['orka_memory:852d7f9ed0fb4a8f9f3b8ab7ef19582b','orka_memory:b8ab1a8cd4a24504a435405f093ed722']
for k in keys:
    s = r.hget(k,'content')
    print('\n---',k)
    if s is None:
        print('(no content)')
    else:
        print(s.decode('utf-8'))