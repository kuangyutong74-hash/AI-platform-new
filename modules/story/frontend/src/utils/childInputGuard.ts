export const CHILD_INPUT_BLOCK_MESSAGE =
  '这句话里可能包含过于具体的个人信息。请不要填写真实住址、学校、班级、电话、姓名或账号密码，改成虚构信息后再继续吧。';

/**
 * Only concrete identifying details are blocked in the browser. Story language
 * is left to the director to understand in context instead of using a word list.
 */
const PRIVATE_DETAIL_PATTERNS = [
  /(?<!\d)1[3-9]\d{9}(?!\d)/,
  /(?<!\d)\d{17}[\dXx](?!\d)/,
  /(?:手机(?:号)?|电话(?:号码)?|联系方式)(?:是|为|：|:)?\s*\d{7,11}/,
  /(?:微信(?:号)?|QQ(?:号)?|邮箱)(?:是|为|：|:)\s*[A-Za-z0-9_.@+-]{4,}/i,
  /(?:我的真实姓名|我的姓名|真实姓名|姓名)(?:是|为|叫|：|:)\s*[\u4e00-\u9fff·]{2,8}/,
  /(?:我(?:在|就读于)|我的学校(?:是|叫|为)|学校(?:是|叫|为))[^，。！？\n]{2,30}(?:学校|小学|中学|高中|大学)/,
  /(?:我是|我在)[一二三四五六七八九十\d]{1,3}年级[\u4e00-\u9fff\d]{0,6}班/,
  /(?:我家住(?:在)?|我住在|家庭住址(?:是|为)?|(?:我的)?地址(?:是|为)?)[^，。！？\n]{0,50}(?:小区|街道|路|街|巷|弄|村|社区|公寓|\d+号|\d+栋|\d+幢|\d+单元|\d+室|\d+楼)/,
  /(?:我的|账号|账户|登录|支付|银行卡)[^，。！？\n]{0,8}(?:密码|口令)(?:是|为|：|:)\s*[^，。！？\s]{3,}/,
  /(?:验证码)(?:是|为|：|:)\s*\d{4,8}/,
];

export function shouldBlockChildInput(text: string): boolean {
  const raw = text.trim();
  return Boolean(raw) && PRIVATE_DETAIL_PATTERNS.some((pattern) => pattern.test(raw));
}
