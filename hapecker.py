#coding: utf-8


import subprocess, os, re
import logging, argparse
import zipfile, json


logging.basicConfig(level = logging.INFO, format='%(asctime)s - %(levelname)s [%(filename)s:%(lineno)d]: %(message)s')


def execShellDaemon(cmd, isWin=True):
  '''
  async
  '''
  if not isWin:
    return subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, preexec_fn=os.setsid) # type: ignore
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


def splitTofiles(sourceFile, outDir):
  logging.info('Split into files...')
  sdir = outDir+'sources/'
  try:
    os.mkdir(sdir)
  except:
    pass
  fileOut = {}  # slower
  errFile = {}
  existFiles = []
  with open(sourceFile, 'r', encoding='utf8') as f:
    started = False
    dirs = []
    currentFile = ''
    out = ''
    fullClassname = ''
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
            if '#' not in line:              
              if line.count('@') != 3:
                logging.error('lib error '+line)
                continue
              tmp = line.split('@')[3].split('(')[0].split('.')
              dirName = 'package/'+'/'.join(tmp[:-2])
              clsName = tmp[-2]
              funName = tmp[-1]+'('+line.split('(')[1]
            else:
              # .function any pkg_modules..ohpm.@hpem+hpem_base@2.4.25.pkg_modules.@hpem.hpem_base.src.main.ets.com.bytedance.hpem.tracker.AbilityLifecycle.#~a0<@1*@3*#(any a0, any a1, any a2, any a3) <static> {
              lis = line.split('#')
              if lis[0].count('@') != 3:
                logging.error('lib error '+line)
                continue
              tmp = lis[0].split('@')[3].split('(')[0].split('.')
              dirName = 'package/'+'/'.join(tmp[:-2])
              clsName = tmp[-2]
              funName = '#'+'#'.join(lis[1:])
          else:
            dirName = 'pkg_modules'
            clsName = 'pkg'
            funName = line.removeprefix('.function any ')
        elif '@' in line:
          # lib ?
          # .function any com.ss.hm.ugc.aweme.entry@account_api.ets.experiment.TrustEnvExperiment.func_main_0(
          tmp = []
          if '#' not in line:
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
            # .function any com.ss.hm.ugc.aweme.entry@live_sdk_impl.ets.s32.x319.#~@0>#bindLiveRouterUrls(any a0, any a1, any a2) <static> {
            lis = line.split('#')
            if lis[0].count('@') > 1:
              logging.error(line)
            li2 = lis[0].replace('@', '._modules_.')
            tmp = li2.split('(')[0].split(' ')[2].split('.')
            if len(tmp) < 3:
              logging.error('ferr '+line)
              continue
            dirName = '/'.join(tmp[:-2])
            clsName = tmp[-2]
            funName = '#'+'#'.join(lis[1:])
          
          fullClassname = '.'.join(tmp[:-1]).replace('._modules_.', '@')
        else:
          tmp = line.split('(')[0].split(' ')[2].split('.')
          if len(tmp) < 3:
            logging.error('ferr '+line)
            continue
          dirName = '/'.join(tmp[:-2])
          clsName = tmp[-2]
          funName = tmp[-1]+'('+line.split('(')[1]
          fullClassname = '.'.join(tmp[:-1])

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
        fullClassname = ''
        out += '}\n'
        try:
          mode = 'w'
          if currentFile in existFiles:
            mode = 'a'
          else:
            existFiles.append(currentFile)
          with open(currentFile, mode, encoding='utf8') as ff:
            ff.write(out)
            out = ''
        except Exception as e:
          # logging.error(e)
          con = errFile.get(currentFile, '')
          errFile[currentFile] = con+out
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
        if fullClassname:
          out += line.replace(fullClassname, 'this')
        else:
          out += line

  errContent = ''
  for k, v in errFile.items():
    try:
      with open(k, 'w', encoding='utf8') as ff:
        ff.write(v)
    except Exception as e:
      # logging.error(e)
      errContent += '=file='+k+'\n'+v+'=file-end=\n\n'
  if errContent:
    logging.info('See errfile(File Not Found error).')
    with open(sdir+'/errfile', 'w', encoding='utf8') as ff:
      ff.write(errContent)

def simplifyy(rawCon, loadVAR, hap):
  out = []
  rawConList = rawCon
  skipNext = False
  for ind, vv in enumerate(rawConList):
    vv = vv.replace('a2.', 'this.')
    v = vv.strip()
    if skipNext:
      skipNext = False
      continue
    nextLine = ''
    if ind < len(rawConList) -1:
      nextLine = rawConList[ind+1]
      nextLine = nextLine.strip()
    if '= '+loadVAR in v:
      # v0 = loadVV
      # v0 = HiSysEventUtil

      # v0 = loadVV
      # v0 = v0.obj

      # v0 = loadVV
      # v0 = v0+obj
      if not nextLine.startswith(v.split()[0]+' =') or '= '+v.split()[0] in nextLine:
        out.append(vv)
    elif v.startswith('//'):
      # //v(v,v)
      # aa = v(v,v)
      if not v.removeprefix('//') in nextLine:
        if v.startswith('//TD '):
          out.append(vv)
        else:
          if ' //' in vv:
            out.append(vv.replace('//', ''))
          else:
            out.append(vv)
    # elif ' = ' in v:
    #   # v0 = v2(v0)
    #   # v1 = v2(v0).errorCode
    #   ttt = v.split(' = ')
    #   if ttt[1].endswith(')') and ttt[1].count(')')==1 and ' = '+ttt[1]+'.' in nextLine:
    #     rawConList[ind+1] = rawConList[ind+1].replace(ttt[1]+'.', ttt[0]+'.')
    #   out.append(vv)
    else:
      out.append(vv)
  mode = 'w'
  if os.path.isfile(hap+'.ss0'):
    mode = 'a'
  outstr = ''.join(out)
  with open(hap+'.ss0', mode, encoding='utf8') as f:
    f.write(outstr)
 
  # per function
  tmp = outstr.split('.function any')
  outout = []
  for tout in tmp:
    tt = tout.split('\n')
    funout = []
    flen = len(tt)

    if flen > 10000:
      logging.info('Too large '+tt[0])
      outout.append(tout)
      continue

    for ind, vv in enumerate(tt):
      tvv = vv.strip()
      if not tvv:
        # funout.append(vv)
        continue
      tv = tvv.split(' = ')
      # if '.ndk_wrapper.ets.Index.setUserData' in tvv:
      #   print(1)
      
      # 值代入
      replacedValue = False
      if len(tv) == 2 and len(tv[1]) < 200:        
        # v1 = a1//xxx
        # v0 = v1(v0) v2 = v0.xx  ===> v2 = v1(v0).xx v2 = v1(v1(v0)) replace multi-times
        if not '//' in tvv and ind < flen-1 and tv[0] not in tv[1]:
          replacedValue = True

          for i in range(ind+1, flen):
            leftcon = '\n'.join(tt[i:])
            if not tv[0] in leftcon:
              break            
            laterBreak = False
            # set value again
            if tt[i].strip().startswith(tv[0]+' = ') or tt[i].strip().startswith(tv[0]+'.') or tt[i].strip().startswith(tv[0]+'['):
              # v6 = v6+".zip"
              # v0 = v2(v0)
              if ' = ' in tt[i] and tv[0] in tt[i].split(' = ')[1]:
                laterBreak = True
              else:
                break
            if tv[0] not in tt[i]:
              continue

            # replace value

            # not function call
            # v3 = (t194@_modules_/lockUtil/ets/login/LoginManager)
            if ( ' = ' not in tt[i] or not '.' in tt[i].split(' = ')[0] ) and (not tv[1].endswith(')') or (tv[1].startswith('(') and '@' in tv[1]) ):
              tt[i] = tt[i].replace(tv[0]+'.', tv[1]+'.')
            if ' = ' not in tt[i] or not '[' in tt[i].split(' = ')[0]:
              tt[i] = tt[i].replace(tv[0]+'[', tv[1]+'[')
            tt[i] = tt[i].replace(tv[0]+'+', tv[1]+'+')
            tt[i] = tt[i].replace(tv[0]+',', tv[1]+',')
            tt[i] = tt[i].replace(tv[0]+')', tv[1]+')')
            tt[i] = tt[i].replace(tv[0]+'(', tv[1]+'(')
            tt[i] = tt[i].replace(tv[0]+'/', tv[1]+'/')            
            try:
              tt[i] = re.sub(tv[0]+'$', tv[1], tt[i]) # type: ignore
            except:
              # ignore when tv contain special chars
              pass
            
            if laterBreak:
              break

      # 去掉未使用值
      changedCon = '\n'.join(tt[ind+1:]).split(tv[0]+' = ')[0]
      used = False
      if tv[0] in changedCon:
        used = True
        if len(tv) == 2:
          # v0, v10
          pattern = re.compile(tv[0]+r'[^\d]+')
          matchs = pattern.findall(changedCon)
          if matchs:
            used = True
          else:
            used = False
      if not replacedValue or '.' in tv[0] or '[' in tv[0] or used:
        # v6.memLevel
        # v6[v3]
        funout.append(vv)
 
    outout.append('\n'.join(funout))
      
  return '\n\n.function any'.join(outout)

def getParamList(startVar, count, start=0, end=0):
  # v5, 2 => v5, v6
  si = int(startVar[1:])
  cc = int(count.strip(','), 16) + end
  out = []
  for i in range(start, cc):
    out.append('v'+str(si+i))
  return ', '.join(out)


def isCommand(sstr:str):
  ins = ['callruntime.isfalse', 'definepropertybyname', 'callruntime.istrue', 'callruntime.ldlazymodulevar', 'wide.getmodulenamespace', 'callruntime.ldsendablevar', 'stsuperbyvalue', 'wide.stlexvar', 'throw.undefinedifholewithname', 'closeiterator', 'stmodulevar', 'jstricteqnull', 'setobjectwithproto', 'apply', 'newobjrange', 'callruntime.createprivateproperty', 'jeqnull', 'noteq', 'stglobalvar', 'shl2', 'tonumeric', 'getmodulenamespace', 'xor2', 'asyncgeneratorreject', 'eq', 'stobjbyvalue', 'asyncfunctionenter', 'newobjapply', 'ldhole', 'createiterresultobj', 'greatereq', 'callrange', 'stownbyvalue', 'wide.ldpatchvar', 'jnstrictequndefined', 'getnextpropname', 'stlexvar', 'newlexenv', 'stownbynamewithnameset', 'callargs3', 'callruntime.ldsendableexternalmodulevar', 'wide.supercallthisrange', 'stricteq', 'wide.ldexternalmodulevar', 'return', 'createemptyarray', 'ldglobalvar', 'ldprivateproperty', 'ldfalse', 'lesseq', 'wide.copyrestargs', 'wide.stobjbyindex', 'jstrictequndefined', 'inc', 'istrue', 'instanceof', 'stprivateproperty', 'ldlocalmodulevar', 'wide.callthisrange', 'jnstricteqz', 'not', 'wide.newobjrange', 'ldundefined', 'ldlexvar', 'ldobjbyindex', 'createobjectwithbuffer', 'asyncfunctionresolve', 'wide.ldobjbyindex', 'exp', 'getiterator', 'mod2', 'setgeneratorstate', 'wide.stownbyindex', 'and2', 'defineclasswithbuffer', 'stobjbyname', 'ldobjbyname', 'suspendgenerator', 'tonumber', 'lda.str', 'jnenull', 'jneundefined', 'or2', 'ldnull', 'createobjectwithexcludedkeys', 'sta', 'jnez', 'callruntime.widestsendablevar', 'ldexternalmodulevar', '.catchall', 'dec', 'callruntime.topropertykey', 'jstricteqz', 'ashr2', 'wide.supercallarrowrange', 'isin', 'starrayspread', 'stsuperbyname', 'ldsymbol', 'callthisrange', 'mov', 'nop', 'copydataproperties', 'ldnewtarget', 'getunmappedargs', 'ldthis', 'jne', 'jeqz', 'returnundefined', 'createregexpwithliteral', 'div2', 'typeof', 'trystglobalbyname', 'jstricteq', 'neg', 'callruntime.stsendablevar', 'debugger', 'asyncfunctionreject', 'stobjbyindex', 'jequndefined', 'throw.undefinedifhole', 'wide.ldlocalmodulevar', 'stownbyvaluewithnameset', 'gettemplateobject', 'callruntime.ldsendableclass', 'creategeneratorobj', 'throw.ifsupernotcorrectcall', 'newlexenvwithname', 'callthis3', 'callthis0', 'callruntime.defineprivateproperty', 'getpropiterator', 'tryldglobalbyname', 'throw.ifnotobject', 'mul2', 'add2', 'dynamicimport', 'delobjprop', 'shr2', 'callruntime.widenewsendableenv', 'callruntime.newsendableenv', 'resumegenerator', 'isfalse', 'ldthisbyvalue', 'ldobjbyvalue', 'callarg1', 'callarg0', 'ldsuperbyname', 'ldfunction', 'poplexenv', 'ldtrue', 'ldglobal', 'jeq', 'throw.patternnoncoercible', 'stthisbyname', 'jnstricteqnull', 'ldsuperbyvalue', 'jmp', 'callthis2', 'copyrestargs', 'callthis1', 'throw.constassignment', 'lda', 'ldai', 'ldbigint', 'definemethod', 'getresumemode', 'createemptyobject', 'callargs2', 'asyncgeneratorresolve', 'sttoglobalrecord', 'stownbyindex', 'throw.deletesuperproperty', 'definefieldbyname', 'jnstricteq', 'supercallarrowrange', 'less', 'asyncfunctionawaituncaught', 'ldthisbyname', 'stconsttoglobalrecord', 'wide.createobjectwithexcludedkeys', 'wide.ldlexvar', 'fldai', 'createasyncgeneratorobj', 'createarraywithbuffer', 'callruntime.callinit', 'ldnan', 'throw.notexists', 'wide.newlexenv', 'wide.newlexenvwithname', 'strictnoteq', 'sub2', 'wide.stpatchvar', 'wide.callrange', 'supercallthisrange', 'wide.stmodulevar', 'callruntime.notifyconcurrentresult', 'stthisbyvalue', 'definegettersetterbyvalue', 'greater', 'ldinfinity', 'testin', 'stownbyname', 'getasynciterator', 'definefunc', 'supercallspread', 'throw']

  sins = ['jump_label_', 'try_begin_label', 'handler_begin_label']

  cmd = sstr.strip().split()[0]
  isCmd = False
  if cmd in ins:
    isCmd = True
  else:
    for s in sins:
      if cmd.startswith(s):
        isCmd = True
        break

  return isCmd

def takecareChinese(s):
  out = s
  try:
    out = s.encode('latin1').decode('utf8', 'ignore')
  except:
    pass

  return out

def simplify(hap, outDir):
  sep = '    '
  subSep = '  '
  out = ''
  outarr = []
  handledCMD = []
  loadVAR = '(loadSlot'
  notTranslate = []
  multi_line_str = ''
  logging.info('Decompile abc...')

  saveFileEncode = 'utf8'
  # create file
  with open(hap+'.ss', 'w', encoding=saveFileEncode) as f:
    f.write('')
  with open(hap+'.ss0', 'w', encoding=saveFileEncode) as f:
    f.write('')
  with open(hap+'.raw', 'w', encoding=saveFileEncode) as f:
    f.write('')

  moduleTag = []
  importLibs = {}
  moduleStart = True
  soModuleMap = {}
  libModuleMap = {}
  
  with open(hap, 'r', encoding='latin1') as f:
    # 'utf-8' codec can't decode byte 0xc0 in position 4718: invalid start byte 2872 0x1b43bb
  # with open(hap, 'r', encoding='utf8') as f:
    started = False
    accValue = 'acc'    
    staNeedReset = ''
    slotInd = ''
    line = ''
    strBegin = False

    moduleStarted = False
    recordStarted = False
    lastLine = ''
    curInd = ''
    clsIndLibMap = {}
    clsLibMap = {}
    curRecordCls = ''

    curFuncls = ''
    funSlotMap = {}

    while True:
      try:
        line = f.readline()
      except Exception as ee:
        logging.error(str(ee)+' '+line)
        line = ''
        outarr.append('\n//*****decode error*****//\n')
        outarr.append('\n//*****{}*****//\n'.format(ee))
      if not line: # at least '\n'
        break

      if line.startswith('# LITERALS'):
        moduleStarted = True
      if moduleStarted:
        if 'MODULE_REQUEST_ARRAY: ' in line:
          curInd = lastLine.split()[1]
        elif 'ModuleTag: ' in line:
          line = line.strip().removesuffix(';')
          tmp = ''
          localname = ''
          importname = ''
          libname = ''
          exportname = ''
          tb = line.split(', ')
          tmpstr = ''
          for t in tb:
            tt = t.split(': ')
            if tt[0] == 'ModuleTag':
              tmp = tt[1]
            elif tt[0] == 'local_name':
              localname = tt[1]
            elif tt[0] == 'import_name':
              importname = tt[1]
            elif tt[0] == 'module_request':
              libname = tt[1]
            elif tt[0] == 'export_name':
              exportname = tt[1]
            else:
              logging.error(line)
              continue
          if tmp == 'REGULAR_IMPORT' or 'NAMESPACE_IMPORT' == tmp:
            if libname.startswith('@app:'):
              tmpstr = libname.split('/')[-1]+'.so'
            else:
              tmplib = libname
              if importname != 'default' and importname != localname:
                tmplib += '.'+importname
              if tmplib.startswith('@bundle:'):
                tmplib = tmplib.split('@')[-1]
                tmplib = '@_modules_/'+tmplib
              elif tmplib.startswith('@package:'):
                tmplib = tmplib.split('@')[-1]
                tmplib = '@package/'+tmplib
              
              tmpstr = localname+tmplib
          elif tmp == 'LOCAL_EXPORT':
            tmpstr = localname

          if tmpstr:
            if curInd in clsIndLibMap.keys():
              clsIndLibMap.get(curInd, []).append(tmpstr)
            else:
              tt = []
              tt.append(tmpstr)
              clsIndLibMap[curInd] = tt
        
      if line.startswith('# RECORDS'):
        moduleStarted = False
        recordStarted = True
      if recordStarted:
        if line.startswith('.record '):
          curRecordCls = line.split()[1]
        elif ' moduleRecordIdx = ' in line:
          cind = line.split(' moduleRecordIdx = ')[1].strip()
          clsLibMap[curRecordCls] = clsIndLibMap.get(cind, [])

      lastLine = line

      # # lib import
      # 已根据.record表进行精准解析
      # 可删掉
      # if moduleStart and 'ModuleTag: ' in line:
      #   # ['LOCAL_EXPORT', 'REGULAR_IMPORT', 'INDIRECT_EXPORT', 'STAR_EXPORT', 'NAMESPACE_IMPORT']
      #   if ']}' in line:
      #     line = line.split(' [ ')[-1]
      #     line = line.split('; ]}')[0]
      #     libs = line.split('; ')
      #   else:
      #     # 分布在多行
      #     line = line.strip().removesuffix(';')
      #     libs = []
      #     libs.append(line)
      #   for lb in libs:
      #     tmp = ''
      #     localname = ''
      #     importname = ''
      #     libname = ''
      #     exportname = ''
      #     tb = lb.split(', ')
      #     for t in tb:
      #       tt = t.split(': ')
      #       if tt[0] == 'ModuleTag':
      #         tmp = tt[1]
      #         if tt[1] not in moduleTag:
      #           moduleTag.append(tt[1])
      #       elif tt[0] == 'local_name':
      #         localname = tt[1]
      #       elif tt[0] == 'import_name':
      #         importname = tt[1]
      #       elif tt[0] == 'module_request':
      #         libname = tt[1]
      #       elif tt[0] == 'export_name':
      #         exportname = tt[1]
      #       else:
      #         logging.error(line)
      #         continue
      #     if tmp == 'REGULAR_IMPORT':
      #       # importLibs.append('import '+importname+' from '+libname+' as '+localname)
      #       if libname.startswith('@app:'):
      #         if localname in soModuleMap.keys() and libname.split('/')[-1] != soModuleMap.get(localname, ''):
      #           logging.error('lib name collision '+ libname+' -local- '+localname)
      #         soModuleMap[localname] = libname.split('/')[-1]
      #       else:
      #         tmplib = libname
      #         if importname != 'default' and importname != localname:
      #           tmplib += '.'+importname
      #         if 'Logger' == localname or libname.endswith('/index') or libname.endswith('/Index'):
      #           continue
      #         tmp = libModuleMap.get(localname, '')
      #         if tmp:
      #           if tmplib not in tmp :
      #             # logging.error('(import)name collision: ('+ tmplib+') and ('+libModuleMap.get(localname, '')+') => '+localname+' (add together)')
      #             tmplib += ' || '+tmp
      #           else:
      #             tmplib = tmp
      #         if tmplib:
      #           libModuleMap[localname] = tmplib
              
      #     elif tmp == 'NAMESPACE_IMPORT' or tmp == 'STAR_EXPORT' or tmp == 'LOCAL_EXPORT':
      #       # importLibs.append('import '+importname+' as '+localname)
      #       pass
      #     elif tmp == 'INDIRECT_EXPORT':
      #       # 'LOCAL_EXPORT' no need
      #       #  INDIRECT_EXPORT impl?
      #       pass
      #       # tmplib = libname
            
      #       # tmp = libModuleMap.get(exportname, '')
      #       # if tmp:
      #       #   if tmplib not in tmp:
      #       #     # logging.error('(export)name collision: ('+ tmplib+') and ('+libModuleMap.get(exportname, '')+') => '+exportname+' (add together)')
      #       #     tmplib += ' || ' + tmp
      #       #   else:
      #       #     tmplib = tmp
      #       # if tmplib:
      #       #   libModuleMap[exportname] = tmplib
      #     else:
      #       logging.error(line)
      #       continue
        
      # if line == '# RECORDS\n':
      #   # print(moduleTag)
      #   # print(importLibs)
      #   moduleStart = False
      #   # print(soModuleMap)
      #   # return

      if line.startswith('.function '):
        started = True
        recordStarted = False
        curFuncls = line.split()[2].split('.')
        curFuncls = '.'.join(curFuncls[:-1])
        outarr.append('\n'+line)
        continue
      elif started and ( line.startswith('L_ESSlotNumberAnnotation:') or line.startswith('# ===========') ):
        # avoid lda.str parse error
        started = False
        # outarr.append('}\n\n')
        accValue = ''

        # Append to file 5M
        if len(outarr) > 5 * 1024 * 1024 / 10:
          # # 替换slot变量，slot可能是函数范围的而不是类范围的，当前做法不准确
          # tf = ''
          # for ind, tl in enumerate(outarr):
          #   if tl.startswith('.function any'):
          #     tf = tl.split()[2].split('.')
          #     tf = '.'.join(tf[:-1])
          #   elif '(loadSlot ' in tl:
          #     # (loadSlot 0x0,0x1)
          #     tt = tl.split('(loadSlot ')[1].split(')')[0]
          #     tv = funSlotMap.get(curFuncls, {}).get(tt, '')
          #     if tv:
          #       print(tl, tv, curFuncls)
          #       outarr[ind] = tl.replace('(loadSlot {})'.format(tt), tv)

          with open(hap+'.raw', 'a', encoding=saveFileEncode) as f2:
            f2.write(''.join(outarr))
          with open(hap+'.ss', 'a', encoding=saveFileEncode) as ff:
            ff.write(simplifyy(outarr, loadVAR, hap))
            outarr = []

        continue

      # https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/arkts-bytecode-fundamentals-V5
      if started:
        code = ''
        try:
          code = line.strip()
          if not code:
            continue
          handledCMD.append(code)
          cmd = code.split()[0]
          tc = code.split()

          if strBegin:
            if isCommand(line):
              strBegin = False
            else:
              multi_line_str += ' '+code
              accValue = takecareChinese(multi_line_str)
              continue

          if code.startswith('lda '):
            accValue = code.split()[1]
          elif code.startswith('lda.str '):
            tmps = ' '.join(tc[1:])
            strBegin = True
            multi_line_str = tmps
            accValue = takecareChinese(multi_line_str)

          elif code.startswith('createobjectwithbuffer '):
            tmps = ' '.join(tc[2:]).strip('"')
            strBegin = True
            multi_line_str = tmps
            accValue = takecareChinese(multi_line_str)

          elif code.startswith('createarraywithbuffer '):
            tmps = ' '.join(tc[2:]).strip('"')
            strBegin = True
            multi_line_str = tmps
            accValue = takecareChinese(multi_line_str)

          elif code.startswith('stownbyindex '):
            outarr.append(sep+tc[2].strip(',')+'['+tc[3]+'] = '+accValue+'\n')
          elif code.startswith('stobjbyindex '):
            outarr.append(sep+tc[2].strip(',')+'['+tc[3]+'] = '+accValue+'\n')
          elif code.startswith('wide.stownbyindex '):
            outarr.append(sep+tc[1].strip(',')+'['+tc[2]+'] = '+accValue+'\n')
          elif code.startswith('wide.stobjbyindex '):
            outarr.append(sep+tc[1].strip(',')+'['+tc[2]+'] = '+accValue+'\n')

          # ld + sta + throw
          # ld + throw
          # ld
          # ld + sta
          elif code.startswith('sta '):
            outarr.append(sep+code.split()[1]+' = '+accValue+'\n')
            if accValue.startswith('(loadSlot'):
              staNeedReset = code.split()[1] +'@slot'+slotInd
          elif cmd in ['callruntime.ldlazymodulevar', 'callruntime.ldsendablevar', 'callruntime.ldsendableexternalmodulevar', 'ldexternalmodulevar', 'ldlocalmodulevar', 'wide.ldlocalmodulevar', 'wide.ldexternalmodulevar', 'wide.ldpatchvar']:
            staNeedReset = ''
            slotInd = '(loadSlot-module {})'.format(tc[1])
            accValue = slotInd
            if cmd == 'ldexternalmodulevar' or cmd == 'wide.ldexternalmodulevar':
              try:
                # 已经根据.record表进行精准解析
                accValue = clsLibMap.get(curFuncls, [])[int(tc[1], 16)]
              except Exception as e:
                logging.error(e)
                logging.error(code)
                logging.error(curFuncls)
                logging.error(clsLibMap.get(curFuncls, []))

          elif cmd in ['ldlexvar', 'wide.ldlexvar']:
            # 当前类或当前函数中，依据save/load index进行对应
            staNeedReset = ''
            slotInd = '(loadSlot {})'.format(''.join(tc[1:]))
            accValue = slotInd

            # 由于各个function的排序问题，load可能会在save之前
            accValue = funSlotMap.get(curFuncls, {}).get(''.join(tc[1:]), accValue)
          elif code.startswith('throw.undefinedifholewithname '):
            if not accValue.startswith('(loadSlot'):
              continue
            
            accValue = tc[1].strip('"')
            if staNeedReset:
              staNeedReset = staNeedReset.split('@slot')[0]
              outarr.append(sep+staNeedReset+' = '+accValue+'\n')
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
            outarr.append(sep+tc[1].strip(',')+'['+tc[2]+'] = '+accValue+'\n')
            accValue = 'len-'+tc[1].strip(',')
          elif code.startswith('ldobjbyname '):
            accValue = accValue+'.'+tc[2].strip('"')
          elif code.startswith('ldobjbyvalue '):
            accValue = tc[2]+'['+accValue+']'
          elif code.startswith('ldsuperbyname '):
            accValue = 'super'+'/'+accValue+'/.'+tc[2].strip('"')
          elif code.startswith('ldsuperbyvalue '):
            accValue = tc[2]+'.super'+'/'+accValue+'/'
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
            outarr.append(sep+'del '+tc[1]+'.'+accValue+'\n')
          elif code.startswith('setobjectwithproto '):
            outarr.append(sep+accValue+'__proto__ = '+tc[2]+'\n')
          elif code.startswith('copydataproperties '):
            outarr.append(sep+tc[1]+' = '+accValue+'\n')
            accValue = tc[1]
          elif code.startswith('stownbyvaluewithnameset '):
            outarr.append(sep+tc[2].strip(',')+'.'+tc[3]+' = '+accValue+'\n')

          elif code.startswith('stownbynamewithnameset '):
            outarr.append(sep+tc[3]+'.'+tc[2].strip(',')+' = '+accValue+'\n')

          elif code.startswith('stobjbyname '):
            outarr.append(sep+tc[3]+'.'+tc[2].strip(',').strip('"') +' = '+accValue+'\n')
          elif code.startswith('stobjbyvalue '):
            outarr.append(sep+tc[2].strip(',')+'.'+tc[3] +' = '+accValue+'\n')
          elif code.startswith('stownbyvalue '):
            outarr.append(sep+tc[2].strip(',')+'.'+tc[3] +' = '+accValue+'\n')

          elif code.startswith('stthisbyvalue '):
            outarr.append(sep+'this.'+tc[2] +' = '+accValue+'\n')
          elif code.startswith('stthisbyname '):
            outarr.append(sep+'this.'+tc[2] +' = '+accValue+'\n')
          elif code.startswith('stsuperbyname '):
            outarr.append(sep+tc[3]+'.super.'+tc[2].strip(',') +' = '+accValue+'\n')

          elif code.startswith('trystglobalbyname '):
            outarr.append(sep+tc[2] +' = '+accValue+'\n')
          elif code.startswith('stglobalvar '):
            outarr.append(sep+tc[2] +' = '+accValue+'\n')
          elif code.startswith('stprivateproperty '):
            outarr.append(sep+tc[4]+'.slot-'+tc[2].strip(',')+'-'+tc[3].strip(',') +' = '+accValue+'\n')
          elif code.startswith('callruntime.defineprivateproperty '):
            outarr.append(sep+tc[4]+'.slot-'+tc[2].strip(',')+'-'+tc[3].strip(',') +' = '+accValue+'\n')
          elif code.startswith('callruntime.createprivateproperty '):
            outarr.append(sep+code+'\n')
          elif code.startswith('callruntime.callinit '):
            outarr.append(sep+'this='+tc[2]+'\n')
            accValue = accValue+'()'
          elif code.startswith('stsuperbyvalue '):
            outarr.append(sep+tc[2].strip(',')+'.super.'+tc[3] +' = '+accValue+'\n')

          elif code.startswith('sttoglobalrecord '):
            outarr.append(sep+tc[2] +' = '+accValue+'\n')
          elif code.startswith('stconsttoglobalrecord '):
            outarr.append(sep+tc[2] +' = '+accValue+'\n')


          elif code.startswith('supercallspread '):
            accValue = accValue+'('+','.join(tc[2:])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('throw.ifsupernotcorrectcall '):
            outarr.append(sep+'throw'+'\n')
          elif code.startswith('throw.ifnotobject '):
            outarr.append(sep+' object !='+tc[1]+'? throw '+'\n')
            
          
          elif cmd in ['stmodulevar', 'wide.stmodulevar']:
            outarr.append(sep+accValue+'(saveSlot-module {})\n'.format(tc[1]))
          elif cmd in ['stlexvar', 'wide.stlexvar']:
            outarr.append(sep+accValue+'(saveSlot {})\n'.format(''.join(tc[1:])))
            tt = {}
            tt[''.join(tc[1:])] = accValue
            if curFuncls in funSlotMap.keys():
              funSlotMap.get(curFuncls, {}).update(tt)
            else:
              funSlotMap[curFuncls] = tt
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
            accValue = tc[2].removesuffix(',')+'(super:'+tc[-1]+')'
          elif code.startswith('definefunc '):
            accValue = tc[2].rstrip(',')
          elif code.startswith('definemethod '):
            accValue = tc[2].rstrip(',')
          elif code.startswith('definefieldbyname ') or code.startswith('callruntime.definefieldbyvalue ') or code.startswith('callruntime.definefieldbyindex ') or code.startswith('definepropertybyname '):
            outarr.append(sep+tc[3]+'.'+tc[2].strip(',').strip('"')+' = '+accValue+'\n')
          elif code.startswith('definegettersetterbyvalue '):
            outarr.append(sep+'//'+tc[1]+'.'+tc[2]+': {get:'+tc[3]+', set:'+tc[4]+'}'+'\n')

          elif code.startswith('isfalse') or code.startswith('callruntime.isfalse'):
            accValue = accValue+' == false'
          elif code.startswith('istrue') or code.startswith('callruntime.istrue'):
            accValue = accValue+' == true'
          elif code.startswith('stricteq '):
            accValue = accValue+' === '+tc[2]
          elif code.startswith('strictnoteq '):
            accValue = accValue+' !== '+tc[2]
          elif code.startswith('eq '):
            accValue = accValue+' == '+tc[2]
          elif code.startswith('noteq '):
            accValue = accValue+' !== '+tc[2]
          elif code.startswith('less '):
            accValue = accValue+' > '+tc[2]
          elif code.startswith('lesseq '):
            accValue = accValue+' >== '+tc[2]
          elif code.startswith('greater '):
            accValue = accValue+' < '+tc[2]
          elif code.startswith('greatereq '):
            accValue = accValue+' <== '+tc[2]
          elif code.startswith('isin '):
            accValue = tc[2] +' in '+accValue
          
          elif code.startswith('jnez '):
            outarr.append(sep+'('+accValue+') != 0 : jmp '+tc[1]+'\n')
          elif code.startswith('jeqz '):
            outarr.append(sep+'('+accValue+') == 0 : jmp '+tc[1]+'\n')

          elif code.startswith('jeq '):
            outarr.append(sep+'('+accValue+') == '+tc[1].strip(',')+' : jmp '+tc[2]+'\n')
          elif code.startswith('jne '):
            outarr.append(sep+'('+accValue+') != '+tc[1].strip(',')+' : jmp '+tc[2]+'\n')
          elif code.startswith('jeqnull '):
            outarr.append(sep+'('+accValue+') == null : jmp '+tc[1]+'\n')
          elif code.startswith('jnenull '):
            outarr.append(sep+'('+accValue+') != null : jmp '+tc[1]+'\n')          
          elif code.startswith('jstricteq '):
            outarr.append(sep+'('+accValue+') === '+tc[1].strip(',')+' : jmp '+tc[2]+'\n')
          elif code.startswith('jnstricteq '):
            outarr.append(sep+'('+accValue+') !== '+tc[1].strip(',')+' : jmp '+tc[2]+'\n')
          elif code.startswith('jequndefined '):
            outarr.append(sep+'('+accValue+') == undefined : jmp '+tc[1]+'\n')
          elif code.startswith('jneundefined '):
            outarr.append(sep+'('+accValue+') != undefined : jmp '+tc[1]+'\n')
          elif code.startswith('jstricteqz '):
            outarr.append(sep+'('+accValue+') === 0 : jmp '+tc[1]+'\n')
          elif code.startswith('jnstricteqz '):
            outarr.append(sep+'('+accValue+') !== 0 : jmp '+tc[1]+'\n')
          elif code.startswith('jstricteqnull '):
            outarr.append(sep+'('+accValue+') === null : jmp '+tc[1]+'\n')
          elif code.startswith('jnstricteqnull '):
            outarr.append(sep+'('+accValue+') !== null : jmp '+tc[1]+'\n')
          elif code.startswith('jstrictequndefined '):
            outarr.append(sep+'('+accValue+') === undefined : jmp '+tc[1]+'\n')
          elif code.startswith('jnstrictequndefined '):
            outarr.append(sep+'('+accValue+') !== undefined : jmp '+tc[1]+'\n')
          elif code.startswith('jmp '):
            outarr.append(sep+code+'\n')

          elif code == 'throw':
            outarr.append(sep+'throw '+accValue+'\n')
          elif code.startswith('throw.notexists'):
            outarr.append(sep+code+'\n')
          elif code.startswith('throw.undefinedifhole'):
            outarr.append(sep+code+'\n')
          elif code.startswith('throw.deletesuperproperty'):
            outarr.append(sep+code+'\n')
          elif code.startswith('throw.patternnoncoercible'):
            outarr.append(sep+code+'\n')
          elif code.startswith('throw.constassignment'):
            outarr.append(sep+code+'\n')

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

          elif code.startswith('createobjectwithexcludedkeys '):
            accValue = tc[2].strip(',')+'(exclude-'+tc[3]+' count:'+tc[1].strip(',')+')'
          elif code.startswith('wide.createobjectwithexcludedkeys '):
            accValue = tc[2].strip(',')+'(exclude-'+tc[3]+' count:'+tc[1].strip(',')+')'


          elif code.startswith('stownbyname '):
            tt = tc[2].strip(',').strip('"')
            outarr.append(sep+tc[3]+'.'+tt+' = '+accValue+'\n')
          elif code.startswith('newobjrange '):
            accValue = tc[3]+'('+getParamList(tc[3], tc[2], 1, 0)+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('wide.newobjrange '):
            accValue = tc[2]+'('+getParamList(tc[2], tc[1], 1, 0)+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callthisrange '):
            accValue = accValue+'('+getParamList(tc[3], tc[2], 1, 1)+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('wide.callthisrange '):
            accValue = accValue+'('+getParamList(tc[2], tc[1], 1, 1)+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callrange '):
            accValue = accValue+'('+getParamList(tc[3], tc[2])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('wide.callrange '):
            accValue = accValue+'('+getParamList(tc[2], tc[1])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('supercallarrowrange '):
            accValue = accValue+'.super('+getParamList(tc[3], tc[2])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('wide.supercallarrowrange '):
            accValue = accValue+'.super('+getParamList(tc[2], tc[1])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callthis0 '):
            accValue = accValue+'()'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callthis1 '):
            accValue = accValue+'('+tc[3]+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callthis2 '):
            accValue = accValue+'('+tc[3]+tc[4]+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callthis3 '):
            accValue = accValue+'('+tc[3]+tc[4]+tc[5]+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callarg0 '):
            accValue = accValue+'()'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callarg1 '):
            accValue = accValue+'('+tc[2]+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callargs2 '):
            accValue = accValue+'('+tc[2]+','+tc[3]+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('callargs3 '):
            accValue = accValue+'('+tc[2]+','+tc[3]+','+tc[4]+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('supercallthisrange '):
            accValue = 'super'+'('+getParamList(tc[3], tc[2])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('wide.supercallthisrange '):
            accValue = 'super'+'('+getParamList(tc[2], tc[1])+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('apply '):
            accValue = tc[2].strip(',')+'.'+accValue+'('+tc[3]+')'
            outarr.append(sep+'//'+accValue+'\n')

          elif code.startswith('mov '):
            # if tc[2] == 'a0':
            #   tc[2] += '//FunctionObject'
            # elif tc[2] == 'a1':
            #   tc[2] += '//NewTarget'
            # elif tc[2] == 'a2':
            #   tc[2] += '//this'
            outarr.append(sep+tc[1].strip(',')+' = '+tc[2]+'\n')

          
          elif cmd in ['wide.newlexenvwithname', 'callruntime.newsendableenv', 'callruntime.stsendablevar', 'callruntime.widestsendablevar','callruntime.widenewsendableenv', 'newlexenvwithname', 'newlexenv', 'wide.newlexenv', 'poplexenv', 'callruntime.ldsendableclass', 'callruntime.notifyconcurrentresult', 'callruntime.topropertykey', 'debugger', 'nop']:
            pass
          elif code.startswith('return'):
            outarr.append(sep+'return '+accValue+'\n')
          elif code.startswith('returnundefined'):
            outarr.append(sep+'return undefined'+'\n')
          elif code.startswith('ldfunction'):
            accValue = 'this'
          elif code.startswith('ldsymbol'):
            accValue = 'Symbol'

          elif code.startswith('wide.stpatchvar '):
            outarr.append(sep+'//TD slot-'+tc[1]+' = '+accValue+'\n')

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
            outarr.append(sep+accValue+'.generator = '+tc[1]+'\n')
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
            # outarr.append(sep+'//TD asyncfunctionreject'+accValue+'\n')
          elif code.startswith('asyncfunctionresolve '):
            accValue = tc[1]+'.Promise.resolve('+accValue+')'
            # outarr.append(sep+'//TD asyncfunctionresolve'+accValue+'\n')


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
            outarr.append(sep+'import '+accValue+'\n')
          
          elif code.startswith('asyncfunctionenter'):
            accValue = 'asyncFun'
          elif code.startswith('asyncfunctionawaituncaught '):
            accValue = 'await '+tc[1] +'('+accValue+')'
            outarr.append(sep+'//'+accValue+'\n')
          elif code.startswith('suspendgenerator '):
            accValue = tc[1]
            outarr.append(sep+'//'+tc[1]+'.suspend()'+'\n')
          elif code.startswith('resumegenerator'):
            outarr.append(sep+'//'+accValue+'.resume()'+'\n')
            
          elif code.startswith('jump_label_'):
            outarr.append(subSep+code+'\n')
          elif code.startswith('try_begin_label'):
            outarr.append(subSep+code+'\n')
          elif code.startswith('handler_begin_label'):
            outarr.append(subSep+code+'\n')
            
          else:
            if not cmd in notTranslate and not cmd.startswith('try_') and not cmd.startswith('handler_') and not cmd.startswith('.catchall') and not cmd == '}':
              outarr.append('*******str error ({})********\n'.format(cmd))
              notTranslate.append(cmd) 
            if code == '}':
              # end of function
              outarr.append('}\n')
            else:
              outarr.append(sep+'//TD '+code+'\n')
        except Exception as e:
          outarr.append(sep+code+'\n')
          logging.error('=error '+code+' '+str(e))
          import traceback
          traceback.print_exc()
  
  if notTranslate:
    logging.info('Not translate '+str(notTranslate))
  with open(hap+'.raw', 'a', encoding=saveFileEncode) as f:
    f.write(''.join(outarr)) # .encode('latin1').decode('utf8')
  with open(hap+'.ss', 'a', encoding=saveFileEncode) as f:
    f.write(simplifyy(outarr, loadVAR, hap))


def disasm(hap, odir, disasmBin):
  doneDisasm = False
  if os.path.isfile(odir+'sources/_disasm'):
    doneDisasm = True
  doneDecompile = False
  if os.path.isfile(odir+'sources/_decompile'):
    doneDecompile = True
  doneSplitfile = False
  if os.path.isfile(odir+'sources/_splitfile'):
    doneSplitfile = True
  
  logging.info('Start '+hap)
  logging.info('Unzip...')  
  zipfile.ZipFile(hap).extractall(odir)
  # logging.info('Need set to path '+disasmBin)
  pp = odir+'ets/'
  for f in os.listdir(pp):
    if f.endswith('.abc'):
      logging.info('Disasm '+f)
      outfile = pp+f+'.ets'
      if forceOverride or not doneDisasm:
        cmd = disasmBin+' '+pp+f+' '+outfile
        out = execShell(cmd)
        if 'e' in out.keys():
          logging.error('Disam error '+str(out))
          continue
      else:
        logging.info('Skip disasm')
      if forceOverride or not doneDecompile:
        simplify(outfile, odir)
      else:
        logging.info('Skip decompile')
      if forceOverride or not doneSplitfile:
        splitTofiles(outfile+'.ss', odir)
      else:
        logging.info('Skip split file')
    elif os.path.isdir(pp+f):
      for f2 in os.listdir(pp+f):
        if f2.endswith('.abc'):
          outfile = pp+f+'/'+f2+'.ets'
          logging.info('Disasm '+f+'/'+f2)
          if forceOverride or not doneDisasm:
            cmd = disasmBin+' '+pp+f+'/'+f2+' '+outfile
            out = execShell(cmd)
            if 'e' in out.keys():
              logging.error('Disam error '+str(out))
              continue
          else:
            logging.info('Skip disasm')
          if forceOverride or not doneDecompile:
            simplify(outfile, odir)
          else:
            logging.info('Skip decompile')
          if forceOverride or not doneSplitfile:
            splitTofiles(outfile+'.ss', odir)
          else:
            logging.info('Skip split file')
  with open(odir+'sources/_disasm', 'w', encoding='utf8') as f:
    f.write('done')
  with open(odir+'sources/_decompile', 'w', encoding='utf8') as f:
    f.write('done')
  with open(odir+'sources/_splitfile', 'w', encoding='utf8') as f:
    f.write('done')

def checkVulns(fileName, content, vulns, out):
  lens = len(content)
  tmpOut = {}
  for k, vv in vulns.items():
    for v in vv:
      start = v[0]
      end = v[1]
      ind = -1
      ind2 = -1
      sliceCode = []
      for i in range(0, lens):
        if ind>-1 and i > ind:
          sliceCode.append(content[i])
          if end == '===noend===':
            break
        if start in content[i]:
          ind = i
          sliceCode.append(content[i])
        elif ind>-1 and end in content[i]:
          ind2 = i       
          tmp = tmpOut.get(k, [])
          tmp.append(''.join(sliceCode))
          tmpOut[k] = tmp
          sliceCode = []
          ind = -1
          
      if ind2 == -1 and ind > -1: # no end
        tmp = tmpOut.get(k, [])
        ed = ind + 5
        if ed> lens -1:
          ed = lens -1
        tmp.append(''.join(content[ind:ed])+'    ===noend===\n')
        tmpOut[k] = tmp

  if tmpOut:
    # single file scan once
    out[fileName] = tmpOut

def doScan(sdir, vulns, out, count):
  # scandir
  with os.scandir(sdir) as entries:
    for entry in entries:
      if entry.is_file():
        count[0] += 1
        try:
          fileName = os.path.join(sdir, entry.name)
          with open(fileName, 'r', encoding='utf8') as t:
            con = t.readlines()
            checkVulns(fileName, con, vulns, out)
        except Exception as e:
          import traceback
          traceback.print_exc()
          logging.error(e)
      elif entry.is_dir():
        doScan(os.path.join(sdir, entry.name), vulns, out, count)
  
def staticScan(source, scan):
  if not scan:
    return
  logging.info('Start static vuln scan...')
  noEnd = '===noend==='
  vulns = {
    "broadcast": [['[ string:"events",', '.events = ']],
    "webview": [['javaScriptProxy\n', '.object = '], 
                ['.runJavaScript\n', noEnd], 
                ['.createWebMessagePorts\n', noEnd], 
                ['.postMessageEvent\n', noEnd]],
    # "account": [['.setCredential\n', noEnd],
    #             ['.setCustomData\n', noEnd],
    #             ['.setAuthToken\n', noEnd],
    #             ['.createAccount\n', noEnd],],
  }
  out = {}
  count = [0]
  doScan(os.path.join(source, 'sources'), vulns, out, count)
  wout = []
  wout.append('Total file:'+str(count))
  for k, v in out.items():
    wout.append('===='+k.removeprefix(source))
    for k2, v2 in v.items():
      wout.append('=='+k2)
      wout.append('='+'\n'.join(v2))
  
  with open(source+'/vuln.info', 'w', encoding='utf8') as f:
    f.write('\n'.join(wout))

def getModuleInfo(hap, odir):
  from io import BytesIO
  logging.info('Parse module.json')
  fd = open(hap, "rb")
  hapCon = fd.read()
  zip = zipfile.ZipFile(BytesIO(hapCon))
  moduleCon = ''
  for i in zip.namelist():
    if i == "module.json":
      moduleCon = zip.read(i)
      break
  
  bundleName = ''
  versionName = ''
  if moduleCon:
    mjson = json.loads(moduleCon)
    out = '=App:'
    app = mjson.get('app', {})
    out += app.get('bundleName', '')+' '+ app.get('versionName', '') +'\n'
    versionName = app.get('versionName', '')
    bundleName = app.get('bundleName', '')
    logging.info('BundleName '+bundleName)

    exportedAbility = []
    noneExported = []
    module = mjson.get('module', {})
    out += '=Application:'+module.get('srcEntrance', '')+' '+module.get('mainElement', '')+ '\n'

    for ab in module.get('abilities', []):
      ex = ab.get('visible', False)
      if not ex:
        ex = ab.get('exported', False)
      deepLink = []
      for sk in module.get('skills', []):
        dp = sk.get('uris', [])
        for d in dp:
          deepLink.append(d.get('scheme', '')+'://'+d.get('host', ''))
      deeplinks = '|'.join(deepLink)
      if deeplinks:
        deeplinks = '({})'.format(deeplinks)
      if ex:
        exportedAbility.append(ab.get('name', '')+': '+ab.get('srcEntrance', '')+' '+deeplinks)
      else:
        noneExported.append(ab.get('name', '')+': '+ab.get('srcEntrance', '')+' '+deeplinks)

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

    bundleName = os.path.basename(hap)
    bundleName = bundleName.removesuffix('.hap')
    bundleName = bundleName.removesuffix('.hsp')

    # print(out)
    if os.path.isfile(odir+bundleName+'/module.info'):
      tc = ''
      with open(odir+bundleName+'/module.info', 'r', encoding='utf8') as f:
        tc = f.read()
      tv = tc.split('\n')[0].split()[-1]
      
      if out != tc and tv[0].isdigit() and versionName == tv:
        logging.info('Multi hap')
        import hashlib
        md5 = hashlib.md5(tc.encode('utf8'))
        bundleName += '-'+md5.hexdigest()
    try:
      os.mkdir(odir+bundleName)
    except:
      pass
    with open(odir+bundleName+'/module.info', 'w', encoding='utf8') as f:
      f.write(out)
  else:
    logging.error('module.json read error')
  
  return bundleName


def doWork(pkg, scan):
  pkg = os.path.abspath(pkg)
  app = getModuleInfo(pkg, os.path.join(curdir, 'apps', ''))
  workdir = os.path.join(curdir, 'apps', app, '')
  if scan != 'only':
    disasm(pkg, workdir, curdir+'disasm/ark_disasm.exe')
  staticScan(workdir, scan)
  logging.info('Done.')

def pullHap(hap, outdir):
  ret = False
  cmd = 'hdc shell "cp '+hap+' /data/local/tmp/tmphap"'
  out = execShell(cmd)
  if 'Permission denied' in str(out):
    logging.error('No perm '+hap)
  else:
    cmd = 'hdc file recv /data/local/tmp/tmphap '+outdir
    out = execShell(cmd)
    if 'FileTransfer finish' not in str(out):
      print(out)
    else:
      ret = True
  return ret

def main(pkgs, scan):
  if pkgs.endswith('.hap') or pkgs.endswith('.hsp'):
    doWork(pkgs, scan)
  else:
    # bm dump -a | cat > /data/local/tmp/pkglist
    # hdc list targets
    # hdc -t 2LQ0224226000002 shell
    for pkg in pkgs.split(','):
      pkg = pkg.strip()
      if not pkg:
        continue
      cmd = 'hdc shell "bm dump -n '+pkg+'"'
      out = execShell(cmd)
      outt = out.get('d', '')
      if not outt:
        outt = out.get('e', '')
      if pkg in outt:
        haps = []
        tmp = outt.split('\n')
        for t in tmp:
          # "hapPath": "/system/app/Screenshot/Screenshot.hap",
          if '"hapPath"' in t:
            tt = t.split('"')[-2]
            if tt not in haps:
              haps.append(tt)
        multi = False
        if len(haps) > 1:
          multi = True
        for ha in haps:
          logging.info(ha)
          tf = ha.split('/')
          subName = '.hap'
          if multi:
            subName = '_'+tf[-1]
          hadir = os.path.join(curdir, 'apps', tf[-2]+subName)
          ret = pullHap(ha, hadir)
          if ret:
            try:
              doWork(hadir, scan)
            except Exception as e:
              logging.error(e)
      else:
        logging.error("Not exist "+pkg)

# simplify('te.st', '')

curdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '')
forceOverride = True
if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Hap reverse', formatter_class=argparse.RawDescriptionHelpFormatter,
  epilog='''
  python3 hapecker.py douyin.hap
  ''')
  parser.add_argument("-p", "--pkg", type=str, help="hap file path")
  parser.add_argument("-s", "--scan", type=str, help="Staic vuln scan(use 'only' to skip source decompile)")
  parser.add_argument("-n", "--noverride", action="store_true", help="force override")
  
  args = parser.parse_args()
  pkg = args.pkg
  scan = args.scan
  forceOverride = not args.noverride

  try:
    if pkg:
      main(pkg, scan)

    else:
      parser.print_help()
  except KeyboardInterrupt:
    logging.info('Ctrl+C')
