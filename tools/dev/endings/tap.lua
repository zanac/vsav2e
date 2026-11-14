-- logs every program ROM read (pc, address) while the game mode ff8004 is the ending (0x0a)
local cpu=manager.machine.devices[':maincpu']
local space=cpu.spaces['program']
local seen={} local count=0
local tap=nil
local active=false
local function handler(offset,data,mask)
  if not active then return data end
  local pc=cpu.state['CURPC'].value
  local k=pc*16777216+offset
  if not seen[k] then seen[k]=true; count=count+1 end
  return data
end
local done=false
ending_tap=space:install_read_tap(0x000000,0x3fffff,'ending',handler)
function on_frame2(f)
  local mode=space:read_u16(0xff8004)
  if space:read_u16(0xff8008)~=2 then mode=0 end
  if mode==0x0a and not active and not done then active=true; print('tap at',f) end
  if active and mode~=0x0a and not done then
    done=true; active=false
    local fh=io.open(os.getenv('TRACE_OUT')..'/reads.txt','w')
    for k,_ in pairs(seen) do fh:write(string.format('%06x %06x\n',k//16777216,k%16777216)) end
    fh:close(); print('reads',count,'end',f); manager.machine:exit()
  end
end
local fh=io.open("/tmp/claude-0/vs/lua/drive.lua"); local src=fh:read("a"); fh:close(); load(src,"drive","t",_ENV)()
