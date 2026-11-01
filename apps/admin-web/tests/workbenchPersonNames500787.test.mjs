// BUG 500787：工作台、客户ROI统计的人员列显示姓名，不显示登录账号。
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {displayPeopleNames} from '../src/personNameFormat.ts';

const names = new Map([['chenjiugen', '陈久根'], ['fanyg', '范应根']]);

test('多人串逐个换成姓名，查不到的保留原文', () => {
  assert.equal(displayPeopleNames(names, 'System、fanyg、chenjiugen'), '系统、范应根、陈久根');
  assert.equal(displayPeopleNames(names, 'ChenJiuGen,张三'), '陈久根、张三');
  assert.equal(displayPeopleNames(names, ''), '—');
});

test('工作台和客户ROI的人员列都走姓名显示', () => {
  const read = file => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8');
  for (const file of ['DashboardOverview.tsx', 'DashboardHearingSchedule.tsx', 'DashboardRejectionReminder.tsx', 'ReportCenterPage.tsx']) {
    assert.match(read(file), /usePeopleNames\(\)/, file);
  }
  const overview = read('DashboardOverview.tsx');
  for (const field of ['manager', 'lawyer', 'agent', 'assistant']) assert.ok(!overview.includes(`{item.${field} || "—"}`), field);
});
