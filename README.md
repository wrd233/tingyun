# Zabbix Hosts YAML 工具说明

这个目录下有两份 Python 脚本，用来处理 Zabbix 主机导出 YAML。

- `zabbix_export_hosts_by_ip.py`
  从 Zabbix API 按 IP 批量导出 host 配置为 YAML。
- `zabbix_add_port_items_from_csv.py`
  读取导出的 `hosts.yaml` 和一份 CSV，检查每个主机是否已经存在指定端口的监听监控项；如果没有，则补充 `item + trigger`。


## 文件列表

- `zabbix_export_hosts_by_ip.py`
- `zabbix_add_port_items_from_csv.py`
- `README.md`


## 脚本一：按 IP 导出 hosts.yaml

### 功能

输入一个 `.txt` 文件，每行一个 IP。

脚本会：

1. 调用 Zabbix API 的 `host.get`，按接口 IP 查找 host
2. 取到对应 `hostid`
3. 调用 `configuration.export`
4. 导出为 YAML 文件

### 输入示例

`ips.txt`

```txt
10.168.17.53
10.175.11.25
```

### 运行方式

```bash
python3 /Users/wangrundong/work/mywork/zabbix_export_hosts_by_ip.py \
  --url https://your-zabbix.example.com/api_jsonrpc.php \
  --token YOUR_API_TOKEN \
  --ip-file /Users/wangrundong/work/mywork/ips.txt \
  --output /Users/wangrundong/work/mywork/hosts.yaml
```

### 输出结果

- 一个 YAML 文件，例如 `hosts.yaml`
- 终端里会打印匹配到的 host
- 如果某些 IP 没找到，也会在终端里列出来


## 脚本二：按 CSV 补充端口监听监控项

### 功能

读取：

1. 第一份脚本导出的 `hosts.yaml`
2. 一份 CSV 文件

然后按 CSV 中的 IP 和“关键应用端口”字段，检查对应 host 下是否已经存在：

```yaml
- name: port_3306
  key: 'net.tcp.listen[3306]'
  interface_ref: if1
  triggers:
    - expression: 'last(/10.190.22.21/net.tcp.listen[3306])=0'
      name: port_3306
      priority: HIGH
```

如果没有，就自动补上。

### CSV 格式

从左到右四列：

1. 服务器 IP
2. 关键应用端口
3. 关键应用进程
4. 监测 URL

示例：

```csv
10.190.22.21,3306,mysql,
10.190.22.23,80,nginx,http://10.190.22.23/grcv5/login.jsp
10.190.22.24,6379、8089、7080,redis、nginx、java,
```

说明：

- 第二列支持多个端口，分隔符可以是 `、`、`,`、空格、`;`
- `无`、空值会被跳过
- `icmp` 这类非数字端口不会被当作监听端口处理，会写入错误报告

### 运行方式

```bash
python3 /Users/wangrundong/work/mywork/zabbix_add_port_items_from_csv.py \
  --hosts-yaml /Users/wangrundong/work/mywork/hosts.yaml \
  --csv-file /Users/wangrundong/work/mywork/ip-port.csv \
  --output /Users/wangrundong/work/mywork/hosts.updated.yaml \
  --error-file /Users/wangrundong/work/mywork/zabbix_port_item_errors.txt
```

### 输出结果

- `hosts.updated.yaml`
  在原始 YAML 基础上补充缺失的 `net.tcp.listen[PORT]` 监控项
- `zabbix_port_item_errors.txt`
  记录跳过项、异常项、统计信息


## 这份 YAML 应该怎么理解

### 1. `host` 不一定是 IP

在 Zabbix 里：

- `host` 是主机技术名
- `name` 是显示名
- `interfaces[].ip` 才是接口 IP

因此会出现两种常见情况：

#### 情况 A：host 名就是 IP

```yaml
- host: 10.190.22.21
  name: 宁波移动-集团法务系统-数据库服务器1
  interfaces:
    - ip: 10.190.22.21
      interface_ref: if1
```

#### 情况 B：host 名不是 IP

```yaml
- host: lt-api-node1
  name: 宁波联通-API-应用服务器1
  interfaces:
    - ip: 10.188.2.81
      interface_ref: if1
```

所以看这份 YAML 时，应该把一条 `host` 记录理解为“一个被监控对象”，而不是简单理解成“一条 IP”。


### 2. 一条 host 下面通常包含什么

常见结构如下：

- `templates`
  这台主机关联了哪些模板
- `groups`
  属于哪些主机组
- `interfaces`
  Zabbix 用哪个 IP / 协议接入这台主机
- `items`
  这台主机直接定义的监控项
- `triggers`
  监控项对应的触发器
- `macros`
  主机级宏

因此你看到的这份导出 YAML，本质上是在描述：

- 主机对象本身
- 主机接口
- 主机和模板、主机组的关系
- 主机级别直接配置的 item / trigger / macro


### 3. 为什么有些 CSV 里的 IP 会报 `HOST NOT FOUND`

因为 CSV 里的对象并不全是“本机监听端口”。

例如下面这些很可能是“远端依赖地址”而不是本机 host：

- `10.169.88.90`
- `172.26.165.20`
- `6.97.202.189`
- `169.169.46.19`

在 YAML 里，它们通常不是单独的 host，而是作为某个主机上的远程检查目标出现，例如：

- `net.tcp.port[ip,port]`
- `net.tcp.service[...]`
- `web.page.perf[url]`

这类对象不应该补成：

```yaml
key: 'net.tcp.listen[port]'
```

因为 `net.tcp.listen[port]` 表示“检查当前被监控主机自己是否在监听这个端口”。


## 当前脚本的处理范围

`zabbix_add_port_items_from_csv.py` 当前只处理这一类情况：

- CSV 中的 IP 能对应到 `hosts.yaml` 里的某个 host
- 这个端口应当被理解为该主机本机监听端口
- 对应 item key 应该是 `net.tcp.listen[PORT]`

它不会自动处理这些情况：

- 远端依赖地址
- HTTP URL 可用性
- TCP 对端连通性
- ICMP 可达性
- 模板中已有但 host 导出里没有展开出来的监控项


## 关于模板重复的问题

这是一个非常重要的限制。

### 当前脚本能避免什么重复

当前脚本会检查 `hosts.yaml` 里这个 host 已经显式存在的 item。

如果 host 自己已经有：

```yaml
key: 'net.tcp.listen[3306]'
```

就不会再重复添加。

### 当前脚本不能完全避免什么重复

如果这个监控项来自模板继承，而不是直接写在 host 下，主机导出的 YAML 里通常看不到“展开后的全部模板 item”。

也就是说：

- Zabbix 页面上这台 host 实际已经有 `net.tcp.listen[3306]`
- 但导出的 `hosts.yaml` 里不一定能看到它
- 此时脚本可能会误判为“缺失”，然后再补一条 host 级 item

### 更稳妥的办法

如果要彻底避免和模板重复，应该直接查询 Zabbix API，而不是只看导出的 host YAML。

推荐思路：

1. 用 `host.get` 查到 host
2. 用 `item.get` 按 `hostid + key_` 查询该主机当前实际已有的 item
3. 如果已经存在，就跳过

这样会比只看导出文件更可靠。


## 为什么第二个脚本要尽量保留原 YAML 格式

最初版本是“整份 YAML 重新序列化输出”。

这样虽然数据正确，但会带来这些副作用：

- 原有单引号风格变化
- 字段顺序可能变化
- 缩进和空行风格可能变化

现在的版本改成了“文本级增量插入”：

- 不重写整份 YAML
- 只把新增的 `items/triggers` 插到对应 host 下
- 原文件大部分内容和样式保持不变

注意：

- 如果输入的 `hosts.yaml` 本身已经是之前被重排过的版本，这个脚本不会自动把样式恢复成最初导出的样子
- 最好始终以“最初导出的原始 `hosts.yaml`”作为输入


## error 文件怎么看

错误报告文件里通常会有三类信息。

### 1. 统计信息

例如：

```txt
Items added: 17
Triggers added: 17
Existing item+trigger unchanged: 26
Hosts not found: 13
```

表示：

- 新增了多少个 item
- 新增了多少个 trigger
- 已存在而跳过了多少项
- 有多少个 IP 没在 `hosts.yaml` 里找到对应 host

### 2. 非数字端口

例如：

```txt
ROW 64: ip=10.175.25.6 has non-numeric port tokens: icmp
```

说明这一行不是监听端口，当前脚本不会处理。

### 3. 找不到 host

例如：

```txt
HOST NOT FOUND: ip=172.26.165.20, ports=9091,9092
```

说明这个 IP 没有作为 host 出现在 `hosts.yaml` 里。

这通常意味着：

- 它不是被监控主机本身
- 它只是某个主机上配置的远程探测目标


## 推荐使用方式

建议每次按下面顺序操作：

1. 先用第一份脚本从 Zabbix 重新导出原始 `hosts.yaml`
2. 再用第二份脚本基于这份原始 YAML 补充端口监听项
3. 查看 `zabbix_port_item_errors.txt`
4. 对 `HOST NOT FOUND` 的记录单独分析，确认它们是否属于远程依赖而不是本机监听


## 当前已知限制

- 只处理 `net.tcp.listen[PORT]`
- 不自动创建 `net.tcp.port[ip,port]`
- 不自动创建 `net.tcp.service[...]`
- 不自动创建 `web.page.perf[url]`
- 不自动展开模板继承项
- 不保证与模板项完全去重


## 后续可扩展方向

如果后续需要，可以继续扩展成：

1. 自动区分“本机监听端口”和“远端依赖端口”
2. 对远端依赖自动生成 `net.tcp.port` 或 `net.tcp.service`
3. 通过 Zabbix API 检查模板继承项，避免和模板重复
4. 输出一份“建议新增项清单”，先人工审核再落到 YAML

