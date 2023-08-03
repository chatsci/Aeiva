# Install MineDojo platform on MacBook Pro with M1 Chip

## Setup Java Environment
I followed the instructions on: [https://docs.minedojo.org/sections/getting_started/install.html#prerequisites](https://docs.minedojo.org/sections/getting_started/install.html#prerequisites)

Specifically, remember to list all installed Java and and export the temurin8 version java:

```
/usr/libexec/java_home -V
export JAVA_HOME=path/to/eclipse/temurin8
```

After run

```
java -version
```
I got

```
openjdk version "1.8.0_332"
OpenJDK Runtime Environment (Temurin)(build 1.8.0_332-b09)
OpenJDK 64-Bit Server VM (Temurin)(build 25.332-b09, mixed mode)
```

## Install MineDojo
I used the following command: (Assume Java JDK 8 is already installed)

```
pip3 install setuptools==65.5.0 pip==21
pip3 install gym==0.21
git clone https://github.com/MineDojo/MineDojo && cd MineDojo
pip install -e .
```

Note: I found that at the end, if I install from source, I cannot remove the source directory. So after resolved all the bugs as follows, I reinstalled minedojo via pip in my conda virtual env:

```
pip install minedojo
```
So I would recommend install via pip rather than from source.


## Debug experience

There are many different bugs when I try to run
```
python scripts/validate_install.py
```

Below, I list all the operations I have done.

### Upgraded gradle
Check the following:
[https://gradle.org/install/](https://gradle.org/install/)

After installed the new gradle, I got:

```
>>> gradle -v

------------------------------------------------------------
Gradle 8.2.1
------------------------------------------------------------

Build time:   2023-07-10 12:12:35 UTC
Revision:     a38ec64d3c4612da9083cc506a1ccb212afeecaa

Kotlin:       1.8.20
Groovy:       3.0.17
Ant:          Apache Ant(TM) version 1.10.13 compiled on January 4 2023
JVM:          1.8.0_332 (Temurin 25.332-b09)
OS:           Mac OS X 10.16 x86_64

```

### Malmo errors

I referred to: [https://github.com/MineDojo/MineDojo/issues/32#issuecomment-1237247417
](https://github.com/MineDojo/MineDojo/issues/32#issuecomment-1237247417)
It says:


> For Deprecated Gradle feature --> Go to Malmo project download latest prebuild version https://github.com/Microsoft/malmo/releases. Then find and replace the Malmo directory in your python package directory @ xxx/minedojo/sim/Malmo on your computer. (Reminder directory shall keep the same name "Malmo")
> 
> For "OpenGL: ERROR RuntimeException: No OpenGL context found in the current thread." (X Error & bad value) --> make sure you run sudo apt update && sudo apt upgrade before you compile the minecraft java program as the same problem has been described in https://stackoverflow.com/questions/28867285/lwjgl-reports-that-opengl-is-not-supported-on-a-modern-nvidia-card. This works for me.
> 
> Before running python Minedojo code, go xxx/minedojo/sim/Malmo/Minecraft/ where your python put minedojo package and execute ./launchClient.sh (for linux/unix) or .\launchClient (for windows, there's a launchClient.bat file) and make sure it can run normally before you start with Minedojo.


Specifically, when I try to run ./launchClient.sh, I got error due to tools.jar, so I did the following:

```
copy tools.jar from 
/Library/Java/JavaVirtualMachines/temurin-8.jdk/Contents/Home/lib
to
/Library/Internet Plug-Ins/JavaAppletPlugin.plugin/Contents/Home/lib

>>> sudo copy XXX XXX
passwd: (For me, it is the same as the passwd when I login to my macbook pro: the name :)
```

Then, it still fail. So I used back the original Malmo in MineDojo installation (i.e., maybe we DON'T need to download latest prebuild version https://github.com/Microsoft/malmo/releases and then find and replace the Malmo directory in your python package directory ). 

Now it can run. But still some error due to 

```
raise NoSuchProcess(self.pid, self._name)
psutil.NoSuchProcess: process no longer exists (pid=50957, name='bash')
```

I removed the 
```
env.close()
```
in the script and it works.

This is not the end of the story: I found the script doesn't always work. Sometimes, I don't need to remvoe the ```env.close()``` and it still works. Sometimes it doesn't work due to errors like

```
...
	at org.apache.http.impl.DefaultBHttpClientConnection.receiveResponseHeader(DefaultBHttpClientConnection.java:163)
	at org.apache.http.impl.conn.CPoolProxy.receiveResponseHeader(CPoolProxy.java:165)
	at org.apache.http.protocol.HttpRequestExecutor.doReceiveResponse(HttpRequestExecutor.java:273)
	at org.apache.http.protocol.HttpRequestExecutor.execute(HttpRequestExecutor.java:125)
	at org.apache.http.impl.execchain.MainClientExec.createTunnelToTarget(MainClientExec.java:473)
	at org.apache.http.impl.execchain.MainClientExec.establishRoute(MainClientExec.java:398)
	at org.apache.http.impl.execchain.MainClientExec.execute(MainClientExec.java:237)
	at org.apache.http.impl.execchain.ProtocolExec.execute(ProtocolExec.java:185)
	at org.apache.http.impl.execchain.RetryExec.execute(RetryExec.java:89)
	at org.apache.http.impl.execchain.RedirectExec.execute(RedirectExec.java:111)
	at org.apache.http.impl.client.InternalHttpClient.doExecute(InternalHttpClient.java:185)
	at org.apache.http.impl.client.CloseableHttpClient.execute(CloseableHttpClient.java:83)
	at org.gradle.internal.resource.transport.http.HttpClientHelper.performHttpRequest(HttpClientHelper.java:148)
	at org.gradle.internal.resource.transport.http.HttpClientHelper.performHttpRequest(HttpClientHelper.java:126)
	at org.gradle.internal.resource.transport.http.HttpClientHelper.executeGetOrHead(HttpClientHelper.java:103)
	at org.gradle.internal.resource.transport.http.HttpClientHelper.performRequest(HttpClientHelper.java:94)
	... 171 more


* Get more help at https://help.gradle.org

BUILD FAILED in 31s


Minecraft process finished unexpectedly. There was an error with Malmo.
```

I suppose it is due to some network connection errors?

Anyway, now it can work.








