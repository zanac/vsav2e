-- logs the file offsets of the sound program the Z80 reads through its bank window during the ending
local main=manager.machine.devices[':maincpu'].spaces['program']
local z=manager.machine.devices[':audiocpu'].spaces['program']
local seen={} local active=false local bank=0
wtap=z:install_write_tap(0xd003,0xd003,'b',function(offset,data,mask) bank=data & 0x0f; return data end)
rtap=z:install_read_tap(0x8000,0xbfff,'r',function(offset,data,mask)
  if active then seen[0x8000+bank*0x4000+(offset-0x8000)]=true end
  return data end)
local done=false
function on_frame2(f)
  local mode=main:read_u16(0xff8004)
  if main:read_u16(0xff8008)~=2 then mode=0 end
  if mode==0x0a and not active and not done then active=true end
  if active and mode~=0x0a then
    done=true; active=false
    local fh=io.open(os.getenv('TRACE_OUT')..'/breads.txt','w')
    for k,_ in pairs(seen) do fh:write(string.format('%05x\n',k)) end
    fh:close(); manager.machine:exit()
  end
end
local fh=io.open("/tmp/claude-0/vs/lua/drive.lua"); local src=fh:read("a"); fh:close(); load(src,"drive","t",_ENV)()
