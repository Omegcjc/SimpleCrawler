import time

class ScreenDisplay(object):
    def __init__(self):
        self.progress_list = list()
        self.progress_name_list = list()
        self.info_list = list()
        self.line = 0
    @staticmethod
    def time_string(duration, ms=False):
        h = int(duration // 3600)
        str_h = str(h) + ':'
        m = int((duration % 3600) // 60)
        str_m = str(m) + ':'
        s = int((duration % 60) // 1)
        str_s = str(s)
        string = str_h + str_m + str_s
        if ms:
            ms = int(((duration % 1) * 1000) // 1)
            string = string + '.' + str(ms)
        return string
    def display(self):
        lines = 0
        # print(f"\033[{self.line}A\033[K", end='')
        print("\033[2J", end='')  # 清除屏幕
        print('-' * 100)
        for item in self.info_list:
            if item['fixed'] or item['new_add']:
                print("\033[K", end='')  # 清除当前行内容
                print(f'[info] {item["name"]}')
                lines += 1
                item['new_add'] = False
        for item in self.progress_list:
            if item['fixed'] or item['new_add'] or item['finished'] < item['total']:
                print("\033[K", end='')  # 清除当前行内容
                print(f'[prog] {item["name"]}: ', end='')
                if item['total'] != 0:
                    ratio = item['finished'] / item['total']
                    round_ratio = round(ratio * 40)
                    string1 = '|' + '=' * round_ratio + ' ' * (40 - round_ratio) + '|'
                    string2 = ' %3.2f%% (%d/%d)' % (ratio * 100, item['finished'], item['total'])
                    print(string1 + string2, end='')
                    lines += 1
                    item['new_add'] = False
                else:
                    string = '=' if item['ok'] else ' '
                    print('|' + 40 * string + '|', end='')
                    print(' %d' % (item['finished']), end='')
                single = None
                abs = lambda number : number if number > 0 else -number
                if item['mean_single'] is not None or item['smooth_single'] is not None:
                    if item['mean_single'] is not None and item['smooth_single'] is not None:
                        diff = abs(item['mean_single'] - item['smooth_single'])
                        try:
                            diff_ratio = (diff / item['mean_single'] + diff / item['smooth_single']) / 2
                        except:
                            diff_ratio = 1
                        single = (1 - 0.5**diff_ratio) * item['mean_single'] + (0.5**diff_ratio) * item['smooth_single']
                    elif item['mean_single']:
                        single = item['mean_single']
                    else:
                        single = item['smooth_single']
                ok_time = item['this_time'] - item['start_time']
                print('[\033[32m' + self.time_string(ok_time) + '\033[0m', end='')
                if single is not None and item['total'] and item['finished']:
                    rest_time = single * (item['total'] - item['finished'])
                    total_time = rest_time + ok_time
                    print(' + \033[31m' + self.time_string(rest_time) + '\033[0m = ' + self.time_string(total_time), end='')
                print(']', end='')
                print()
                # print(item['mean_single'], item['smooth_single'], end='')
                # if single:
                #     print(single)
        print('-' * 100)
    def info(self, name, fixed=True):
        new_info = {
            'name': name,
            'fixed': fixed,
            'new_add': True
        }
        self.info_list.append(new_info)
        self.display()
    def progress(self, name, finished=None, total=None, ok=False, fixed=False):
        if name not in self.progress_name_list:
            new_info = {
                'name': name,
                'finished': finished,
                'total': total,
                'fixed': fixed,
                'new_add': True,
                'ok': ok,
                'start_time': time.time(),
                'last_time': None,
                'this_time': time.time(),
                'mean_single': None,
                'smooth_single': None
            }
            if finished is None:
                new_info['finished'] = 0
            if total is None:
                new_info['total'] = 0
            self.progress_name_list.append(name)
            self.progress_list.append(new_info)
        else:
            index = self.progress_name_list.index(name)
            new_info = self.progress_list[index]
            new_add = 1
            if finished is None and not ok:
                new_info['finished'] += 1
            elif finished is None:
                new_add = 0
                pass
            else:
                new_add = finished - new_info['finished']
                new_info['finished'] = finished
            if total is not None:
                new_info['total'] = total
            new_info['new_add'] = True
            # 是否完成
            if new_info['finished'] >= new_info['total'] or ok:
                new_info['ok'] = True
                new_info['total'] = new_info['finished']
            # 单个项目的时间
            new_info['last_time'] = new_info['this_time']
            new_info['this_time'] = time.time()
            if new_info['finished']:
                new_info['mean_single'] = (new_info['this_time'] - new_info['start_time']) / new_info['finished']
            if new_add:
                if new_info['smooth_single'] is None:
                    new_info['smooth_single'] = new_info['mean_single']
                else:
                    abs = lambda number: number if number > 0 else -number
                    new_single = (new_info['this_time'] - new_info['last_time']) / abs(new_add)
                    if new_add < 0:
                        new_single = new_single + new_info['smooth_single']
                    diff = abs(new_info['mean_single'] - new_single)
                    try:
                        diff_ratio = (diff / new_info['mean_single'] + diff / new_single) / 2
                    except:
                        diff_ratio = 1
                    factor = (0.75 ** diff_ratio) ** (new_add * 0.5)
                    new_info['smooth_single'] = new_info['smooth_single'] * factor + (1 - factor) * new_single / new_add
        self.display()

if __name__ == '__main__':
    pass