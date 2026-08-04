import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('./src/IprCenterPage.tsx', import.meta.url), 'utf8');

test('IPR detail pagination has three independent state envelopes', () => {
  assert.match(source, /type IprDetailPageState = \{ page: number; pageSize: number; total: number; pages: number \};/);
  assert.match(source, /type IprDetailPagePayload<T> = \{ items\?: T\[\]; total\?: number; page\?: number; page_size\?: number; pages\?: number \};/);
  assert.match(source, /const IPR_DETAIL_DEFAULT_PAGE = 1;/);
  assert.match(source, /const IPR_DETAIL_DEFAULT_PAGE_SIZE = 15;/);
  assert.match(source, /const \[filesPageState, setFilesPageState\] = useState<IprDetailPageState>\(\{\s*page: IPR_DETAIL_DEFAULT_PAGE,\s*pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,\s*total: 0,\s*pages: 0,\s*\}\);/);
  assert.match(source, /const \[remindersPageState, setRemindersPageState\] = useState<IprDetailPageState>\(\{\s*page: IPR_DETAIL_DEFAULT_PAGE,\s*pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,\s*total: 0,\s*pages: 0,\s*\}\);/);
  assert.match(source, /const \[assistedFeesPageState, setAssistedFeesPageState\] = useState<IprDetailPageState>\(\{\s*page: IPR_DETAIL_DEFAULT_PAGE,\s*pageSize: IPR_DETAIL_DEFAULT_PAGE_SIZE,\s*total: 0,\s*pages: 0,\s*\}\);/);
});

test('IPR detail loaders send page and page_size params', () => {
  assert.match(source, /const loadIprFiles = async \([\s\S]*nextPage = filesPageState\.page,[\s\S]*nextPageSize = filesPageState\.pageSize,[\s\S]*api\.get<IprDetailPagePayload<Attachment>>\([\s\S]*\/files[\s\S]*params: \{ page: nextPage, page_size: nextPageSize \}/);
  assert.match(source, /const loadReminders = async \([\s\S]*nextPage = remindersPageState\.page,[\s\S]*nextPageSize = remindersPageState\.pageSize,[\s\S]*api\.get<IprDetailPagePayload<IprReminder>>\([\s\S]*\/reminders[\s\S]*params: \{ page: nextPage, page_size: nextPageSize \}/);
  assert.match(source, /const loadAssistedFees = async \([\s\S]*nextPage = assistedFeesPageState\.page,[\s\S]*nextPageSize = assistedFeesPageState\.pageSize,[\s\S]*api\.get<IprDetailPagePayload<AssistedFee>>\([\s\S]*\/assisted-fees[\s\S]*params: \{ page: nextPage, page_size: nextPageSize \}/);
});

test('IPR detail loaders consume total page page_size and pages', () => {
  assert.match(source, /setFilesPageState\(\{\s*page: data\.page \?\? nextPage,\s*pageSize: data\.page_size \?\? nextPageSize,\s*total: data\.total \?\? data\.items\?\.length \?\? 0,\s*pages: data\.pages \?\? 0,\s*\}\);/);
  assert.match(source, /setRemindersPageState\(\{\s*page: data\.page \?\? nextPage,\s*pageSize: data\.page_size \?\? nextPageSize,\s*total: data\.total \?\? data\.items\?\.length \?\? 0,\s*pages: data\.pages \?\? 0,\s*\}\);/);
  assert.match(source, /setAssistedFeesPageState\(\{\s*page: data\.page \?\? nextPage,\s*pageSize: data\.page_size \?\? nextPageSize,\s*total: data\.total \?\? data\.items\?\.length \?\? 0,\s*pages: data\.pages \?\? 0,\s*\}\);/);
});

test('IPR detail tables bind server pagination objects', () => {
  assert.match(source, /const filesPagination = \{\s*current: filesPageState\.page,\s*pageSize: filesPageState\.pageSize,\s*total: filesPageState\.total,[\s\S]*loadIprFiles\(detail\.id, nextPage, nextPageSize\)/);
  assert.match(source, /const remindersPagination = \{\s*current: remindersPageState\.page,\s*pageSize: remindersPageState\.pageSize,\s*total: remindersPageState\.total,[\s\S]*loadReminders\(detail\.id, nextPage, nextPageSize\)/);
  assert.match(source, /const assistedFeesPagination = \{\s*current: assistedFeesPageState\.page,\s*pageSize: assistedFeesPageState\.pageSize,\s*total: assistedFeesPageState\.total,[\s\S]*loadAssistedFees\(detail\.id, nextPage, nextPageSize\)/);
  assert.match(source, /pagination=\{filesPagination\}\s*dataSource=\{attachments\}/);
  assert.match(source, /pagination=\{assistedFeesPagination\}\s*dataSource=\{assistedFees\}/);
  assert.match(source, /pagination=\{remindersPagination\}\s*dataSource=\{reminders\}/);
});

test('IPR detail pagination is not locally faked', () => {
  assert.match(source, /pagination=\{filesPagination\}/);
  assert.match(source, /pagination=\{assistedFeesPagination\}/);
  assert.match(source, /pagination=\{remindersPagination\}/);
  assert.match(source, /^(?![\s\S]*dataSource=\{attachments\.slice\s*\()[\s\S]*$/);
  assert.match(source, /^(?![\s\S]*dataSource=\{assistedFees\.slice\s*\()[\s\S]*$/);
  assert.match(source, /^(?![\s\S]*dataSource=\{reminders\.slice\s*\()[\s\S]*$/);
  assert.match(source, /^(?![\s\S]*pagination=\{false\}\s*dataSource=\{attachments\})[\s\S]*$/);
  assert.match(source, /^(?![\s\S]*pagination=\{false\}\s*dataSource=\{assistedFees\})[\s\S]*$/);
  assert.match(source, /^(?![\s\S]*pagination=\{false\}\s*dataSource=\{reminders\})[\s\S]*$/);
});
