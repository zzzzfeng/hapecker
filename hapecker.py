#coding: utf-8


import subprocess, sys, os
import threading, time
import logging, argparse
import shutil
import zipfile


logging.basicConfig(level = logging.INFO, format='%(asctime)s - %(levelname)s [%(filename)s:%(lineno)d]: %(message)s')


def execShellDaemon(cmd, isWin=True):
  '''
  async
  '''
  if not isWin:
    return subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=os.setsid)
  return subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

def execShell(cmd, t=120):
  '''
  sync
  haskey('d') == success, only cmd success, should check output
  '''
  ret = {}
  try:
    p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, timeout=t)
    
    if p.returncode == 0:
      try:
        ret['d'] = p.stdout.decode('utf-8')
      except:
        ret['d'] = p.stdout.decode('gbk')
    else:
      try:
        ret['e'] = p.stderr.decode('utf-8')
      except:
        ret['e'] = p.stderr.decode('gbk')
      
  except subprocess.TimeoutExpired:
    ret['e'] = 'timeout'
  except Exception as e:
    logging.error('subprocess '+str(e))

  return ret

def staticScan(source):
  pass

def splitTofiles(sourceFile, outDir):
  logging.info('Split into files...')
  sdir = outDir+'sources/'
  try:
    os.mkdir(sdir)
  except:
    pass
  fileOut = {}  # slower
  with open(sourceFile, 'r', encoding='utf8') as f:
    started = False
    dirs = []
    currentFile = ''
    out = ''
    while True:
      line = f.readline()
      if not line: # at least '\n'
        break
      if line.startswith('.function '):
        started = True

        if line.startswith('.function any pkg_modules'):
          # function pkg_modules..ohpm.AliyunFaceGuard@95hk0jkt00ayejc0wtys5davotk=.pkg_modules.AliyunFaceGuard.AliyunFaceGuard.func_main_0(
          # function pkg_modules..ohpm.@douyin+common_dto@31.4.5.pkg_modules.@douyin.common_dto.src.main.ets.api.v2.feed_common.com_ss_ugc_aweme_SearchMusicCreateInfo(
          if line.startswith('.function any pkg_modules..ohpm.@'):
            if line.count('@') != 3:
              logging.error('lib error '+line)
              continue
            tmp = line.split('@')[3].split('(')[0].split('.')
            dirName = 'libs/'+'/'.join(tmp[:-2])
            clsName = tmp[-2]
            funName = tmp[-1]+'('+line.split('(')[1]
          else:
            dirName = 'pkg_modules'
            clsName = 'pkg'
            funName = line.removeprefix('.function any ')
        elif '@' in line:
          # lib ?
          # .function any com.ss.hm.ugc.aweme.entry@account_api.ets.experiment.TrustEnvExperiment.func_main_0(
          if line.count('@') > 1:
            logging.error(line)
          line = line.replace('@', '._modules_.')
          tmp = line.split('(')[0].split(' ')[2].split('.')
          if len(tmp) < 3:
            logging.error('ferr '+line)
            continue
          dirName = '/'.join(tmp[:-2])
          clsName = tmp[-2]
          funName = tmp[-1]+'('+line.split('(')[1]
        else:
          tmp = line.split('(')[0].split(' ')[2].split('.')
          if len(tmp) < 3:
            logging.error('ferr '+line)
            continue
          dirName = '/'.join(tmp[:-2])
          clsName = tmp[-2]
          funName = tmp[-1]+'('+line.split('(')[1]

        try:
          if dirName not in dirs:
            os.makedirs(sdir+dirName)
            dirs.append(dirName)
        except:
          pass
        currentFile = sdir+dirName+'/'+clsName+'.ets'
        out += '\n'+'function '+funName
        
      elif started and line.startswith('}\n'):
        started = False
        out += '}\n\n'
        try:
          with open(currentFile, 'a', encoding='utf8') as ff:
            ff.write(out)
            out = ''
        except Exception as e:
          logging.error(e)
          out = ''

        # fileOut[currentFile] = fileOut.get(currentFile, '') +'\n'+out
        # out = ''
        # if len(fileOut) > 10:
        #   for k, v in fileOut.items():
        #     try:
        #       with open(k, 'a', encoding='utf8') as ff:
        #         ff.write(v)
                
        #     except Exception as e:
        #       logging.error(e)

        #   fileOut = {}
        
      elif started:
        out += line

  # for k, v in fileOut.items():
  #   try:
  #     with open(k, 'a', encoding='utf8') as ff:
  #       ff.write(v)
  #   except Exception as e:
  #     logging.error(e)



def simplifyy(rawCon, loadVAR):
  out = []
  rawConList = rawCon.split('\n')
  skipNext = False
  for ind, vv in enumerate(rawConList):
    v = vv.strip()
    if skipNext:
      skipNext = False
      continue
    nextLine = ''
    if ind < len(rawConList) -1:
      nextLine = rawConList[ind+1]
      nextLine = nextLine.strip()
    if v.endswith('= '+loadVAR):
      # v0 = loadVV
      # v0 = HiSysEventUtil
      if not nextLine.startswith(v.split()[0]+' ='):
        out.append(vv)
    elif v.startswith('//'):
      if not v.removeprefix('//') in nextLine:
        if v.startswith('//TD '):
          out.append(vv)
        else:
          out.append(vv.replace('//', ''))
    else:
      out.append(vv)
  
  return '\n'.join(out)


def simplify(hap, outDir):
  sep = '    '
  subSep = '  '
  out = ''
  handledCMD = []
  loadVAR = 'loadVV'
  notTranslate = []
  multi_line = False
  multi_line_buffer = False
  multi_line_str = ''
  logging.info('Decompile abc...')
  
  #create file
  with open(hap+'.ss', 'w', encoding='utf8') as f:
    f.write(simplifyy(out, loadVAR))
  
  with open(hap, 'r', encoding='latin1') as f:
    started = False
    accValue = 'acc'    
    staNeedReset = ''
    while True:
      try:
        line = f.readline()
      except Exception as ee:
        logging.error(str(ee)+' '+line)
        line = ''
        out += '\n//*****decode error*****//\n'
        out += '\n//*****{}*****//\n'.format(ee)
      if not line: # at least '\n'
        break

      

      if line.startswith('.function '):
        started = True
        out += '\n'+line
        continue
      elif started and ( line.startswith('L_ESSlotNumberAnnotation:') or line.startswith('# ====================\n') ):
        # avoid lda.str parse error
        started = False
        # out += '}\n\n'

        # Append to file 5M
        if len(out) > 5 * 1024 * 1024:
          with open(hap+'.ss', 'a', encoding='utf8') as ff:
            ff.write(simplifyy(out, loadVAR))
            out = ''

        continue

      if started:
        try:
          code = line.strip()
          if not code:
            continue
          handledCMD.append(code)
          cmd = code.split()[0]
          tc = code.split()

          if multi_line:
            if code != '"' and code != '}"':
              if code.startswith('"'):
                multi_line_str += ' '+code
                continue
              if not code.endswith('"'):
                multi_line_str += ' '+code
                continue
            
            multi_line_str += ' '+code
            accValue = multi_line_str
            multi_line = False
            multi_line_str = ''
            continue
          
          else:
            if code == '"' or code == '}"':
              if len(handledCMD) > 4:
                logging.error(' # '.join(handledCMD[-5:]))
              else:
                logging.error(' # '.join(handledCMD))

          if multi_line_buffer:
            if not code.endswith("]}"):
              multi_line_str += ' '+code
              continue
            multi_line_str += ' '+code
            accValue = multi_line_str
            multi_line_buffer = False
            multi_line_str = ''
            continue

          if code.startswith('lda '):            
            accValue = code.split()[1]
          elif code.startswith('lda.str '):
            tmps = ' '.join(tc[1:])
            # print('start='+tmps+'=')
            # multi-line
            if not tmps.endswith('"') or tmps == '"':
              multi_line = True
              
            multi_line_str = tmps
            accValue = multi_line_str

          elif code.startswith('stownbyindex '):
            out += sep+tc[2].strip(',')+'['+tc[3]+'] = '+accValue+'\n'
          elif code.startswith('stobjbyindex '):
            out += sep+tc[2].strip(',')+'['+tc[3]+'] = '+accValue+'\n'
          elif code.startswith('wide.stownbyindex '):
            out += sep+tc[1].strip(',')+'['+tc[2]+'] = '+accValue+'\n'
          elif code.startswith('wide.stobjbyindex '):
            out += sep+tc[1].strip(',')+'['+tc[2]+'] = '+accValue+'\n'

          elif code.startswith('sta '):
            out += sep+code.split()[1]+' = '+accValue+'\n'
            if accValue == loadVAR:
              staNeedReset = code.split()[1]
          elif cmd in ['callruntime.ldsendablevar', 'callruntime.ldsendableexternalmodulevar', 'ldexternalmodulevar', 'ldlexvar', 'ldlocalmodulevar', 'wide.ldlexvar', 'wide.ldlocalmodulevar', 'wide.ldexternalmodulevar', 'wide.ldpatchvar']:
            accValue = loadVAR
            staNeedReset = ''
          elif code.startswith('throw.undefinedifholewithname '):
            if accValue != loadVAR:
              logging.error('#'.join(handledCMD[-3:]) + ' #'+accValue+' #'+loadVAR)
              out += "****lda.str error ????**** \n"

            accValue = tc[1].strip('"')
            if staNeedReset:
              out += sep+staNeedReset+' = '+accValue+'\n'
              staNeedReset = ''
            

          elif code.startswith('ldbigint '):
            accValue = 'BigInt('+code.split()[1]+')'
          elif code.startswith('ldai '):
            accValue = code.split()[1]
          elif code.startswith('fldai '):
            accValue = code.split()[1]
          elif code.startswith('copyrestargs '):
            ta = 'a'+str(3+int(code.split()[1], 16))
            accValue = ta
          elif code.startswith('wide.copyrestargs '):
            ta = 'a'+str(3+int(code.split()[1], 16))
            accValue = ta
          elif code.startswith('getunmappedargs'):
            accValue = 'arguments'

          elif code.startswith('starrayspread '):
            # array copy
            out += sep+tc[1].strip(',')+'['+tc[2]+'] = '+accValue+'\n'
            accValue = 'len-'+tc[1].strip(',')
          elif code.startswith('ldobjbyname '):
            accValue = accValue+'.'+tc[2].strip('"')
          elif code.startswith('ldobjbyvalue '):
            accValue = tc[2]+'['+accValue+']'
          elif code.startswith('ldsuperbyname '):
            accValue = 'super.'+tc[2]+'//'+accValue
          elif code.startswith('ldsuperbyvalue '):
            accValue = tc[2]+'.super'+'//'+accValue
          elif code.startswith('ldthisbyname '):
            accValue = 'this.'+tc[2]
          elif code.startswith('ldobjbyindex '):
            accValue = accValue+'.'+tc[2]
          elif code.startswith('wide.ldobjbyindex '):
            accValue = accValue+'.'+tc[1]
          elif code.startswith('ldprivateproperty '):
            accValue = accValue+'.slot-'+tc[2].strip(',')+'-'+tc[3]
          elif code.startswith('ldnewtarget'):
            accValue = 'NewTarget'
          elif code.startswith('ldthisbyvalue '):
            accValue = 'this.'+'//'+accValue
          elif code.startswith('ldglobalvar '):
            accValue = tc[2]

          elif code.startswith('delobjprop '):
            out += sep+'del '+tc[1]+'.'+accValue+'\n'
          elif code.startswith('setobjectwithproto '):
            out += sep+accValue+'__proto__ = '+tc[2]+'\n'
          elif code.startswith('copydataproperties '):
            out += sep+tc[1]+' = '+accValue+'\n'
            accValue = tc[1]
          elif code.startswith('stownbyvaluewithnameset '):
            out += sep+tc[2].strip(',')+'.'+tc[3]+' = '+accValue+'\n'

          elif code.startswith('stownbynamewithnameset '):
            out += sep+tc[3]+'.'+tc[2].strip(',')+' = '+accValue+'\n'

          elif code.startswith('stobjbyname '):
            out += sep+tc[3]+'.'+tc[2].strip(',').strip('"') +' = '+accValue+'\n'
          elif code.startswith('stobjbyvalue '):
            out += sep+tc[2].strip(',')+'.'+tc[3] +' = '+accValue+'\n'
          elif code.startswith('stownbyvalue '):
            out += sep+tc[2].strip(',')+'.'+tc[3] +' = '+accValue+'\n'

          elif code.startswith('stthisbyvalue '):
            out += sep+'this.'+tc[2] +' = '+accValue+'\n'
          elif code.startswith('stthisbyname '):
            out += sep+'this.'+tc[2] +' = '+accValue+'\n'
          elif code.startswith('stsuperbyname '):
            out += sep+tc[3]+'.super.'+tc[2].strip(',') +' = '+accValue+'\n'

          elif code.startswith('trystglobalbyname '):
            out += sep+tc[2] +' = '+accValue+'\n'
          elif code.startswith('stglobalvar '):
            out += sep+tc[2] +' = '+accValue+'\n'
          elif code.startswith('stprivateproperty '):
            out += sep+tc[4]+'.slot-'+tc[2].strip(',')+'-'+tc[3].strip(',') +' = '+accValue+'\n'
          elif code.startswith('callruntime.defineprivateproperty '):
            out += sep+tc[4]+'.slot-'+tc[2].strip(',')+'-'+tc[3].strip(',') +' = '+accValue+'\n'
          elif code.startswith('callruntime.createprivateproperty '):
            out += sep+code+'\n'
          elif code.startswith('callruntime.callinit '):
            out += sep+'this='+tc[2]+'\n'
            accValue = accValue+'()'
          elif code.startswith('stsuperbyvalue '):
            out += sep+tc[2].strip(',')+'.super.'+tc[3] +' = '+accValue+'\n'

          elif code.startswith('sttoglobalrecord '):
            out += sep+tc[2] +' = '+accValue+'\n'
          elif code.startswith('stconsttoglobalrecord '):
            out += sep+tc[2] +' = '+accValue+'\n'


          elif code.startswith('supercallspread '):
            accValue = accValue+'('+','.join(tc[2:])+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('throw.ifsupernotcorrectcall '):
            out += sep+'throw'+'\n'
          elif code.startswith('throw.ifnotobject '):
            out += sep+' object !='+tc[1]+'? throw '+'\n'
            
          
          elif cmd in ['stmodulevar', 'stlexvar', 'wide.stlexvar', 'wide.stmodulevar']:
            out += sep+'//TD slot- '+accValue+'(save)\n'
          elif code.startswith('createemptyobject'):
            accValue = 'OBJ'
          elif code.startswith('createemptyarray '):
            accValue = '[]'
          elif code.startswith('newobjapply '):
            accValue = tc[2]+'('+accValue+')'

          elif code.startswith('ldundefined'):
            accValue = 'undefined'
          elif code.startswith('ldnull'):
            accValue = 'null'
          elif code.startswith('ldtrue'):
            accValue = 'true'
          elif code.startswith('ldfalse'):
            accValue = 'false'
          elif code.startswith('ldhole'):
            accValue = 'hole'
          elif code.startswith('ldthis'):
            accValue = 'this'
          elif code.startswith('ldglobal'):
            accValue = 'global'
          elif code.startswith('ldnan'):
            accValue = 'NaN'
          elif code.startswith('ldinfinity'):
            accValue = 'infinity'

          elif code.startswith('tryldglobalbyname '):
            accValue = tc[2].strip('"')
          elif code.startswith('defineclasswithbuffer ') or code.startswith('callruntime.definesendableclass'):
            accValue = tc[2]
          elif code.startswith('definefunc '):
            accValue = tc[2]
          elif code.startswith('definemethod '):
            accValue = tc[2]
          elif code.startswith('definefieldbyname ') or code.startswith('callruntime.definefieldbyvalue ') or code.startswith('callruntime.definefieldbyindex '):
            out += sep+tc[3]+'.'+tc[2].strip(',').strip('"')+' = '+accValue+'\n'
          elif code.startswith('definegettersetterbyvalue '):
            out += sep+'//'+tc[1]+'.'+tc[2]+': {get:'+tc[3]+', set:'+tc[4]+'}'+'\n'

          elif code.startswith('isfalse'):
            accValue = accValue+' == false'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('istrue'):
            accValue = accValue+' == true'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('stricteq '):
            accValue = accValue+' === '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('strictnoteq '):
            accValue = accValue+' !== '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('eq '):
            accValue = accValue+' == '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('noteq '):
            accValue = accValue+' !== '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('less '):
            accValue = accValue+' > '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('lesseq '):
            accValue = accValue+' >== '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('greater '):
            accValue = accValue+' < '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('greatereq '):
            accValue = accValue+' <== '+tc[2]
            out += sep+'//'+accValue+'\n'
          elif code.startswith('isin '):
            accValue = tc[2] +' in '+accValue
            out += sep+'//'+accValue+'\n'
          
          elif code.startswith('jnez '):
            out += sep+'('+accValue+') != 0 : jmp '+tc[1]+'\n'
          elif code.startswith('jeqz '):
            out += sep+'('+accValue+') == 0 : jmp '+tc[1]+'\n'

          elif code.startswith('jeq '):
            out += sep+'('+accValue+') == '+tc[1].strip(',')+' : jmp '+tc[2]+'\n'
          elif code.startswith('jne '):
            out += sep+'('+accValue+') != '+tc[1].strip(',')+' : jmp '+tc[2]+'\n'
          elif code.startswith('jeqnull '):
            out += sep+'('+accValue+') == null : jmp '+tc[1]+'\n'
          elif code.startswith('jnenull '):
            out += sep+'('+accValue+') != null : jmp '+tc[1]+'\n'          
          elif code.startswith('jstricteq '):
            out += sep+'('+accValue+') === '+tc[1].strip(',')+' : jmp '+tc[2]+'\n'
          elif code.startswith('jnstricteq '):
            out += sep+'('+accValue+') !== '+tc[1].strip(',')+' : jmp '+tc[2]+'\n'
          elif code.startswith('jequndefined '):
            out += sep+'('+accValue+') == undefined : jmp '+tc[1]+'\n'
          elif code.startswith('jneundefined '):
            out += sep+'('+accValue+') != undefined : jmp '+tc[1]+'\n'
          elif code.startswith('jstricteqz '):
            out += sep+'('+accValue+') === 0 : jmp '+tc[1]+'\n'
          elif code.startswith('jnstricteqz '):
            out += sep+'('+accValue+') !== 0 : jmp '+tc[1]+'\n'
          elif code.startswith('jstricteqnull '):
            out += sep+'('+accValue+') === null : jmp '+tc[1]+'\n'
          elif code.startswith('jnstricteqnull '):
            out += sep+'('+accValue+') !== null : jmp '+tc[1]+'\n'
          elif code.startswith('jstrictequndefined '):
            out += sep+'('+accValue+') === undefined : jmp '+tc[1]+'\n'
          elif code.startswith('jnstrictequndefined '):
            out += sep+'('+accValue+') !== undefined : jmp '+tc[1]+'\n'
          elif code.startswith('jmp '):
            out += sep+code+'\n'

          elif code.startswith('throw'):
            out += sep+'throw '+accValue+'\n'
          elif code.startswith('throw.notexists'):
            out += sep+code+'\n'
          elif code.startswith('throw.undefinedifhole'):
            out += sep+code+'\n'
          elif code.startswith('throw.deletesuperproperty'):
            out += sep+code+'\n'
          elif code.startswith('throw.patternnoncoercible'):
            out += sep+code+'\n'
          elif code.startswith('throw.constassignment'):
            out += sep+code+'\n'

          elif code.startswith('wide.getmodulenamespace'):
            accValue = 'getmodulenamespace('+tc[1]+')'
          elif code.startswith('getmodulenamespace'):
            accValue = 'getmodulenamespace('+tc[1]+')'
          elif code.startswith('testin '):
            accValue = 'slot-'+tc[2].strip(',')+'-'+tc[3] + ' in ' + accValue
          

          elif code.startswith('tonumber '):
            accValue = 'ToNumber('+accValue+')'
          elif code.startswith('tonumeric '):
            accValue = 'ToNumeric('+accValue+')'
          elif code.startswith('add2 '):
            accValue = tc[2]+'+'+accValue
          elif code.startswith('sub2 '):
            accValue = tc[2]+'-'+accValue
          elif code.startswith('div2 '):
            accValue = tc[2]+'/'+accValue
          elif code.startswith('mul2 '):
            accValue = tc[2]+'*'+accValue
          elif code.startswith('mod2 '):
            accValue = tc[2]+'%'+accValue
          elif code.startswith('or2 '):
            accValue = tc[2]+'|'+accValue
          elif code.startswith('xor2 '):
            accValue = tc[2]+'^'+accValue
          elif code.startswith('and2 '):
            accValue = tc[2]+'&'+accValue
          elif code.startswith('shr2 '):
            accValue = tc[2]+'>>>'+accValue
          elif code.startswith('ashr2 '):
            accValue = tc[2]+'>>'+accValue
          elif code.startswith('shl2 '):
            accValue = tc[2]+'<<'+accValue
          elif code.startswith('exp '):
            accValue = tc[2]+'**'+accValue

          elif code.startswith('createobjectwithbuffer '):
            accValue = ' '.join(tc[2:]).strip('"')
            if not accValue.endswith(']}'):
              multi_line_buffer = True
          elif code.startswith('createarraywithbuffer '):
            accValue = ' '.join(tc[2:]).strip('"')
            if not accValue.endswith(']}'):
              multi_line_buffer = True
          elif code.startswith('createobjectwithexcludedkeys '):
            accValue = tc[2].strip(',')+'(exclude-'+tc[3]+' count:'+tc[1].strip(',')+')'
          elif code.startswith('wide.createobjectwithexcludedkeys '):
            accValue = tc[2].strip(',')+'(exclude-'+tc[3]+' count:'+tc[1].strip(',')+')'


          elif code.startswith('stownbyname '):
            tt = tc[2].strip(',').strip('"')
            out += sep+tc[3]+'.'+tt+' = '+accValue+'\n'
          elif code.startswith('newobjrange '):
            accValue = tc[3]+'('+tc[3]+'+1...'+tc[3]+'+'+tc[2].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('wide.newobjrange '):
            accValue = tc[2]+'('+tc[2]+'+1...'+tc[2]+'+'+tc[1].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callthisrange '):
            accValue = accValue+'(this-'+tc[3]+'+1...'+tc[3]+'+'+tc[2].strip(',')+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('wide.callthisrange '):
            accValue = accValue+'(this-'+tc[2]+'+1...'+tc[2]+'+'+tc[1].strip(',')+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callrange '):
            accValue = accValue+'('+tc[3]+'+1...'+tc[3]+'+'+tc[2].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('wide.callrange '):
            accValue = accValue+'('+tc[2]+'+1...'+tc[2]+'+'+tc[1].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('supercallarrowrange '):
            accValue = accValue+'.super('+tc[3]+'+1...'+tc[3]+'+'+tc[2].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('wide.supercallarrowrange '):
            accValue = accValue+'.super('+tc[2]+'+1...'+tc[2]+'+'+tc[1].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callthis0 '):
            accValue = accValue+'()'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callthis1 '):
            accValue = accValue+'('+tc[3]+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callthis2 '):
            accValue = accValue+'('+tc[3]+tc[4]+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callthis3 '):
            accValue = accValue+'('+tc[3]+tc[4]+tc[5]+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callarg0 '):
            accValue = accValue+'()'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callarg1 '):
            accValue = accValue+'('+tc[2]+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callargs2 '):
            accValue = accValue+'('+tc[3]+tc[3]+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('callargs3 '):
            accValue = accValue+'('+tc[2]+tc[3]+tc[4]+')'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('supercallthisrange '):
            accValue = 'super'+'('+tc[3]+'+1...'+tc[3]+'+'+tc[2].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('wide.supercallthisrange '):
            accValue = 'super'+'('+tc[2]+'+1...'+tc[2]+'+'+tc[1].strip(',')+'-1)'
            out += sep+'//'+accValue+'\n'
          elif code.startswith('apply '):
            accValue = tc[2].strip(',')+'.'+accValue+'('+tc[3]+')'
            out += sep+'//'+accValue+'\n'

          elif code.startswith('mov '):
            if tc[2] == 'a0':
              tc[2] += '//FunctionObject'
            elif tc[2] == 'a1':
              tc[2] += '//NewTarget'
            elif tc[2] == 'a2':
              tc[2] += '//this'
            out += sep+tc[1].strip(',')+' = '+tc[2]+'\n'

          
          elif cmd in ['wide.newlexenvwithname', 'callruntime.newsendableenv', 'callruntime.stsendablevar', 'callruntime.widestsendablevar','callruntime.widenewsendableenv', 'newlexenvwithname', 'newlexenv', 'wide.newlexenv', 'returnundefined', 'poplexenv', 'callruntime.ldsendableclass', 'callruntime.notifyconcurrentresult', 'callruntime.topropertykey', 'debugger', 'nop']:
            pass
          elif code.startswith('return'):
            out += sep+'return '+accValue+'\n'
          elif code.startswith('ldfunction'):
            accValue = 'this'
          elif code.startswith('ldsymbol'):
            accValue = 'Symbol'

          elif code.startswith('wide.stpatchvar '):
            out += sep+'//TD slot-'+tc[1]+' = '+accValue+'\n'

          elif code.startswith('getnextpropname '):
            accValue = tc[1]+'.next()'
          elif code.startswith('getpropiterator'):
            accValue = accValue+'.iterator()'
          elif code.startswith('getiterator '):
            accValue = accValue+'.iterator()'
          elif code.startswith('closeiterator '):
            accValue = tc[2]+'.closeiterator()'
          elif code.startswith('getasynciterator '):
            accValue = accValue+'.async_iterator()'
          elif code.startswith('createiterresultobj '):
            accValue = 'iterator(obj:'+tc[1]+', bool:'+tc[2]+')'
          elif code.startswith('creategeneratorobj '):
            accValue = tc[1]+'.generator'
          elif code.startswith('setgeneratorstate '):
            out += sep+accValue+'.generator = '+tc[1]+'\n'
          elif code.startswith('asyncgeneratorresolve '):
            accValue = tc[1].strip(',')+'.generatorresolve('+tc[2]+tc[3]+')'
          elif code.startswith('getresumemode'):
            accValue = accValue+'.generator()'
          elif code.startswith('createasyncgeneratorobj'):
            accValue = tc[1]+'.asyncgenerator'
          elif code.startswith('asyncgeneratorreject '):
            accValue = tc[1]+'.asyncgenerator.reject(exception:'+accValue+')'
          
          elif code.startswith('asyncfunctionreject '):
            accValue = tc[1]+'.Promise.reject('+accValue+')'
            # out += sep+'//TD asyncfunctionreject'+accValue+'\n'
          elif code.startswith('asyncfunctionresolve '):
            accValue = tc[1]+'.Promise.resolve('+accValue+')'
            # out += sep+'//TD asyncfunctionresolve'+accValue+'\n'


          elif code.startswith('createregexpwithliteral '):
            accValue = 'Regex('+tc[2].strip(',')+', '+tc[3]+')'
          elif code.startswith('gettemplateobject '):
            accValue = 'GetTemplateObject('+accValue+')'

          elif code.startswith('typeof '):
            accValue = 'typeof '+accValue
          elif code.startswith('not '):
            accValue = '~'+accValue
          elif code.startswith('neg '):
            accValue = '-'+accValue
          elif code.startswith('inc '):
            accValue = accValue+' +1'
          elif code.startswith('dec '):
            accValue = accValue+' -1'
          elif code.startswith('instanceof '):
            accValue = tc[2]+' instanceof '+accValue
          

          elif code.startswith('dynamicimport'):
            out += sep+'import '+accValue+'\n'
          
          elif code.startswith('asyncfunctionenter'):
            accValue = 'asyncFun'
          elif code.startswith('asyncfunctionawaituncaught '):
            accValue = 'await '+tc[1] +' '+accValue
            out += sep+'//'+accValue+'\n'
          elif code.startswith('suspendgenerator '):
            accValue = tc[1]
            out += sep+'//'+tc[1]+'.suspend()'+'\n'
          elif code.startswith('resumegenerator'):
            out += sep+'//'+accValue+'.resume()'+'\n'
            
          elif code.startswith('jump_label_'):
            out += subSep+code+'\n'
          elif code.startswith('try_begin_label'):
            out += subSep+code+'\n'
          elif code.startswith('handler_begin_label'):
            out += subSep+code+'\n'
            
          else:
            if not cmd in notTranslate and not cmd.startswith('try_') and not cmd.startswith('handler_') and not cmd.startswith('.catchall') and not cmd == '}':
              out += '*******str error ({})********\n'.format(cmd)
              notTranslate.append(cmd) 
            if code == '}':
              # end of function
              out += '}\n'
            else:
              out += sep+'//TD '+code+'\n'
        except Exception as e:
          out += sep+code+'\n'
          logging.error('=error '+code+' '+str(e))
          import traceback
          traceback.print_exc()
  
  if notTranslate:
    logging.info('Not translate '+str(notTranslate))
  with open(hap+'.ss', 'a', encoding='utf8') as f:
    f.write(simplifyy(out, loadVAR))

  splitTofiles(hap+'.ss', outDir)

def disasm(hap):
  logging.info('Unzip...')
  curdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '')
  odir = os.path.join(curdir, 'apps', os.path.basename(hap)+'.e', '')
  zipfile.ZipFile(hap).extractall(odir)
  disasmBin = curdir+'disasm/ark_disasm.exe'
  # logging.info('Need set to path '+disasmBin)
  pp = odir+'ets/'
  for f in os.listdir(pp):
    if f.endswith('.abc'):
      logging.info('Disasm '+f)
      outfile = pp+f+'.ets'
      cmd = disasmBin+' '+pp+f+' '+outfile
      out = execShell(cmd)
      simplify(outfile, odir)
      # print(out)
    elif os.path.isdir(pp+f):
      for f2 in os.listdir(pp+f):
        if f2.endswith('.abc'):
          outfile = pp+f+'/'+f2+'.ets'
          logging.info('Disasm '+f+'/'+f2)
          cmd = disasmBin+' '+pp+f+'/'+f2+' '+outfile
          out = execShell(cmd)
          simplify(outfile, odir)
          # print(out)
      
  return odir

def getModuleInfo(hap):
  # simplify(hap, '')
  # return
  import json
  logging.info('Start '+hap)

  # disasm and decompile
  modulePath = disasm(hap)

  moduleCon = open(modulePath+'module.json', "r", encoding='utf8').read()
  logging.info('Parse module.json')
  if moduleCon:
    mjson = json.loads(moduleCon)
    out = '=App:'
    app = mjson.get('app', {})
    out += app.get('bundleName', '')+' '+ app.get('versionName', '') +'\n'

    exportedAbility = []
    noneExported = []
    module = mjson.get('module', {})
    out += '=Application:'+module.get('srcEntrance', '')+' '+module.get('mainElement', '')+ '\n'

    for ab in module.get('abilities', []):
      ex = ab.get('visible', False)
      if not ex:
        ex = ab.get('exported', False)
      if ex:
        exportedAbility.append(ab.get('name', '')+': '+ab.get('srcEntrance', ''))
      else:
        noneExported.append(ab.get('name', '')+': '+ab.get('srcEntrance', ''))

    for ab in module.get('extensionAbilities', []):
      ex = ab.get('visible', False)
      if not ex:
        ex = ab.get('exported', False)
      if ex:
        exportedAbility.append(ab.get('name', '')+': '+ab.get('srcEntry', '')+'-'+ab.get('type', ''))
      else:
        noneExported.append(ab.get('name', '')+': '+ab.get('srcEntry', '')+'-'+ab.get('type', ''))
    
    out += '=Exported:\n '+'\n '.join(exportedAbility) + '\n\n'
    out += '=None-Exported:\n '+'\n '.join(noneExported)

    print(out)
    with open(modulePath+'module.info', 'w', encoding='utf8') as f:
      f.write(out)
    logging.info('Done')
  else:
    logging.error('module.json read error')

def getExposed(pkg):
  if pkg.endswith('.hap'):
    getModuleInfo(pkg)
  else:
    logging.error("python3 hapecker.py -p xxx.hap")


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Hap reverse', formatter_class=argparse.RawDescriptionHelpFormatter,
  epilog='''
  python3 hapecker.py douyin.hap
  ''')
  parser.add_argument("-p", "--pkg", type=str, help="hap file path")
  parser.add_argument("-m", type=str, help="hap file path")
  parser.add_argument("-s", "--scan", type=str, help="Staic vuln scan")
  
  args = parser.parse_args()
  pkg = args.pkg

  try:
    if pkg:
      getExposed(pkg)

    else:
      parser.print_help()
  except KeyboardInterrupt:
    logging.info('Ctrl+C')
