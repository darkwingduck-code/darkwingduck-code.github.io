---
title: "SQL正規化の原理と実践上の妥協：1NF・2NF・3NF・BCNF"
date: 2026-07-21 09:50:00 +0900
categories: [Data Engineering, Database Design]
tags: [sql, normalization, 1nf, 2nf, 3nf, bcnf, functional-dependency, data-modeling]
description: "関数従属性と候補キーから出発して1NF・2NF・3NF・BCNFを判定し、無損失分解・従属性保存・非正規化の実践的な基準まで整理する。"
math: true
lang: ja-JP
translation_key: sql-normalization-1nf-2nf-3nf-bcnf
hidden: true
---

{% include language-switcher.html %}

正規化は、表を数多く分割するための規則ではない。核心は、**一つの事実を一か所だけで管理し、更新異常を減らすこと**である。正しく適用するには、column名ではなく、業務規則である関数従属性（functional dependency）を先に記述しなければならない。

本稿では、次の流れで正規形を判定する。

$$
\text{業務規則}
\rightarrow
\text{関数従属性}
\rightarrow
\text{候補キー}
\rightarrow
\text{正規形}
\rightarrow
\text{無損失・従属性保存分解}
$$

## 1. 正規化が防ぐ三つの異常

一つのrelationに異なる事実を重複して保存すると、次の問題が生じる。

- **Update anomaly**：同じ事実が複数のrowにあり、一部だけが修正される。
- **Insert anomaly**：別の事実がなければ、独立した事実を登録できない。
- **Delete anomaly**：一つのrowを削除すると、別個の唯一の事実も一緒に失われる。

たとえば注文rowごとに顧客の表示名を繰り返し保存すると、名前の変更時に過去のすべてのrowを更新しなければならない。一方、「注文当時の表示名」を保存する要件であれば、繰り返しではなく意図したsnapshotかもしれない。正規化の要否はcolumnの形ではなく、**その値が現在の事実か、歴史的事実か**によって決まる。

## 2. 関数従属性：データではなく規則

relation \(R\)のattribute集合\(X,Y\)について

$$
X\to Y
$$

は、同じ\(X\)値を持つ二つのtupleが、必ず同じ\(Y\)値を持たなければならないことを意味する。\(X\)が\(Y\)を関数的に決定する。

注意すべきなのは、現在のsampleで偶然重複がないからといって、関数従属性が生じるわけではないという点である。従属性は、今後入ってくるすべての有効なデータに適用される業務規則でなければならない。

### 自明な従属性

\(Y\subseteq X\)なら、\(X\to Y\)は自明である。たとえば

$$
\{A,B\}\to A
$$

は、値の意味に関係なく常に成り立つ。

### 閉包

attribute集合\(X\)の閉包\(X^+\)は、与えられた関数従属性によって\(X\)が決定できるすべてのattributeである。候補キーの判定は閉包によって行う。

1. \(X^+=X\)から始める。
2. \(Y\to Z\)で\(Y\subseteq X^+\)なら、\(Z\)を\(X^+\)へ追加する。
3. 変化しなくなるまで繰り返す。
4. \(X^+=R\)なら、\(X\)はsuperkeyである。
5. \(X\)のどのproper subsetもsuperkeyでなければ、candidate keyである。

## 3. キー用語を正確に区別する

- **Superkey**：rowを一意に識別するattribute集合。不要なattributeを含むことがある。
- **Candidate key**：これ以上小さくできないminimal superkey。
- **Primary key**：候補キーのうち、実装で代表として選んだキー。
- **Alternate key**：選ばれなかった残りの候補キー。
- **Prime attribute**：少なくとも一つの候補キーに含まれるattribute。
- **Foreign key**：他のrelationのcandidate/unique keyを参照するattribute。

自動増分IDをprimary keyとして追加しても、元の業務上の候補キーと関数従属性は消えない。たとえば重複を禁止すべき自然キーには、別途`UNIQUE` constraintが必要である。

## 4. 1NF：attributeはrelation内で一つの値を持つ

第一正規形は、各tupleとattributeの交点が、そのdomainの単一の値を持たなければならないという関係モデルの原則である。繰り返しcolumnや一つのcell内の可変長リストは、別のrelationへ分離するのが一般的である。

誤った形：

| item_id | labels |
|---|---|
| 一つの識別子 | コンマで連結された複数のlabel |

正規化した形：

~~~sql
CREATE TABLE item (
    item_id BIGINT PRIMARY KEY
);

CREATE TABLE label (
    label_id BIGINT PRIMARY KEY,
    label_name TEXT NOT NULL UNIQUE
);

CREATE TABLE item_label (
    item_id BIGINT NOT NULL REFERENCES item(item_id),
    label_id BIGINT NOT NULL REFERENCES label(label_id),
    PRIMARY KEY (item_id, label_id)
);
~~~

### 「Atomic」はデータ型の大きさではなく、問い合わせ上の意味である

日付を年・月・日の三つのcolumnに分けなければ1NFにならないわけではない。日付domainを一つの値として扱うなら、日付columnはatomicである。反対に、住所文字列全体を一つの値として保存しても1NF違反ではない場合があるが、都市別の検索と検証が必要なら、別の構造の方が適切である。

JSONやarray typeの使用も、すぐに1NF違反だと断定するのではなく、次を問う。

- 内部要素を関係モデルのconstraintやjoinの対象として扱う必要があるか？
- 一部の要素だけを独立して更新するか？
- cardinalityと重複規則をDBが保証する必要があるか？
- schema evolutionが必要な外部payloadか？

## 5. 2NF：複合候補キーの一部だけに依存する事実を除去する

第二正規形は、

1. 1NFであり、
2. すべてのnon-prime attributeが、どの候補キーのproper subsetにも関数的に従属しない状態である。

つまり、partial dependencyを除去する。候補キーが単一attributeだけなら、2NF違反は発生しない。

次のrelationを考えよう。

~~~text
order_line(
  order_id,
  product_id,
  order_time,
  customer_id,
  customer_name,
  product_name,
  quantity,
  agreed_unit_price
)
~~~

一つの注文で同じ商品が一行しか存在しないなら、候補キーは\((order\_id, product\_id)\)である。業務規則が次のとおりだとする。

$$
order\_id\to order\_time, customer\_id
$$

$$
product\_id\to product\_name
$$

$$
(order\_id,product\_id)
\to quantity,agreed\_unit\_price.
$$

`order_time`と`customer_id`はキーの一部である`order_id`だけに、`product_name`は`product_id`だけに依存するため、2NFに違反する。

これを次のように分離する。

- order_header(order_id, order_time, customer_id)
- product(product_id, product_name)
- order_line(order_id, product_id, quantity, agreed_unit_price)

ここでagreed unit priceは商品の現在価格ではなく、その注文行で合意された価格であるため、複合キー全体に依存する。名前が似ているという理由でproduct relationへ移すと、歴史的事実が壊れる。

## 6. 3NF：非キーattributeを介する間接的な従属性を除去する

第三正規形の直感は、non-key attributeが、keyではない別のattributeを介して間接的に決定されないようにすることである。

上の例で、

$$
order\_id\to customer\_id
$$

かつ

$$
customer\_id\to customer\_name
$$

なら、

$$
order\_id\to customer\_name
$$

というtransitive dependencyが生じる。顧客の現在の名前を注文ごとに保存すると更新異常が生じるため、

- customer(customer_id, current_name)
- order_header(order_id, order_time, customer_id)

に分離する。

### 3NFの正確な判定式

すべてのnontrivialな関数従属性\(X\to A\)について、次のいずれかが真なら3NFである。

1. \(X\)がsuperkeyである。
2. \(A\)がprime attributeである。

「non-keyがnon-keyを決定したら必ず違反」という暗記より、この定義の方が候補キーを複数持つrelationでは正確である。

## 7. BCNF：すべての決定項がsuperkey

Boyce–Codd Normal Formでは、すべてのnontrivialな関数従属性\(X\to Y\)において、\(X\)がsuperkeyであることを要求する。

$$
X\to Y\text{ が非自明}
\quad\Longrightarrow\quad
X\text{ はsuperkeyである}.
$$

BCNFは3NFより強い。

$$
\mathrm{BCNF}\subseteq\mathrm{3NF}.
$$

すべてのBCNF relationは3NFだが、すべての3NF relationがBCNFとは限らない。

### 3NFだがBCNFではない例

relation

~~~text
assignment(student, course, instructor)
~~~

に、次の規則があるとする。

1. 一人の学生は一つのcourseで一人のinstructorに割り当てられる。
2. 各instructorは、ちょうど一つのcourseだけを担当する。

関数従属性は、

$$
(student,course)\to instructor
$$

$$
instructor\to course
$$

である。候補キーは\((student,course)\)と\((student,instructor)\)である。したがって、すべてのattributeがprimeであり、3NFの条件を満たす。

しかし、`instructor`単独はsuperkeyでないにもかかわらず`course`を決定するため、BCNFに違反する。

BCNF分解は、

- instructor_course(instructor, course)
- student_instructor(student, instructor)

とできる。重複は減るが、元の\((student,course)\to instructor\) constraintを個々のtableのlocal constraintだけで検査するのは難しい場合がある。ここで、BCNFとdependency preservationとのtradeoffが現れる。

## 8. 優れた分解の二つの条件

### 無損失結合

分解したrelationをnatural joinしたとき、偽のtupleを生まず元のrelationを復元できなければならない。

二つのrelation \(R_1,R_2\)へ分解する場合、次のいずれかが関数従属性の閉包で成り立てばlosslessである。

$$
(R_1\cap R_2)\to R_1
$$

または

$$
(R_1\cap R_2)\to R_2.
$$

共通attributeが、少なくとも一方のrelationでkeyの役割を果たす必要がある、という直感である。

### 従属性保存

元の関数従属性をjoinせず、各relationのlocal constraintで強制できるならdependency-preservingである。

3NF synthesisは、lossless joinとdependency preservationを同時に達成するのに有利である。BCNF decompositionはlosslessにできるが、必ずしもすべての従属性を保存するとは限らない。したがって、「より高い正規形が必ずよりよいschema」とは限らない。

## 9. 実践的な正規化ワークフロー

### ステップ1：事実を文にする

ERDより先に、次の形式で業務規則を記す。

- 一つのAは複数のBを持てる。
- 各Bは、ちょうど一つのCに属する。
- 価格は現在の属性か、取引時点のsnapshotか？
- 識別子は全期間を通じて再利用されないか？

### ステップ2：候補キーと関数従属性を記す

primary keyだけを見ず、すべての候補キーを見つける。unique constraint、nullable column、時間的な有効性まで含める。

### ステップ3：minimal coverを求める

- 右辺を単一のattributeに分解する。
- 左辺の不要なattributeを除去する。
- 他の従属性から導出できる冗長な従属性を除去する。

### ステップ4：正規形を判定する

1NFから始め、2NF、3NF、BCNFの順に上げる。各違反には、実際のupdate/insert/delete anomalyの例を一つ結び付ける。

### ステップ5：分解の品質を確認する

lossless joinとdependency preservationを検証する。constraintが複数のtableにまたがる場合は、transaction、trigger、assertionの代替案、application invariantを明記する。

### ステップ6：物理schemaを設計する

PK、UNIQUE、FK、NOT NULL、CHECK、indexを追加する。FK columnにindexが自動生成されると仮定せず、使用するDBMSを確認する。

### ステップ7：実際のqueryとwrite pathで評価する

query plan、cardinality、lock、write amplification、storageを測定する。パフォーマンス上の問題が確認された箇所だけを意図的にdenormalizeする。

## 10. 非正規化が合理的な場合

正規化は、logical source of truthを設計する際のデフォルトである。次の場合には派生表現を設けてもよい。

### 読み取り性能

頻繁なaggregateや複数のjoinが実際のボトルネックなら、materialized view、indexed view、summary tableを検討する。元のrelationとrefreshポリシーを明記する。

### 分析モデル

OLAPのstar schemaはfactとdimensionを中心に、queryの単純さとscan効率を優先する。これはOLTP source schemaをそのまま置き換えるのではなく、変換済みのserving modelと捉える方が安全である。

### Eventとsnapshot

変更不可能なevent payloadでは、当時の状態を保存するため一部の値を重複させてもよい。現在のmaster dataと過去のevent truthを区別する。

### 外部文書の保存

外部API payloadを原形のまま保存する必要があるなら、raw JSONと正規化したquery tableを併置できる。raw payloadを唯一のquery modelとして使用すると、constraintとmigrationが難しくなる場合がある。

非正規化には必ず次のものを併せて設ける。

- authoritative source
- 更新主体
- 同期・非同期のrefresh方式
- 許容するstaleness
- 再構築手順
- 不一致を検知するquery

## 11. 時間と履歴は別の次元

「顧客の名前」は、現在値一つとは限らない。

- 現在のcanonical name
- 注文当時の表示name
- 特定の有効期間におけるlegal name
- 元のeventに含まれるraw name

temporal requirementがあるなら、`valid_from`、`valid_to`、system time、event timeを区別する。現在のtableを正規化した後、履歴が必要になったとき単純に上書きすると、再現性が失われる。

## 12. 検証チェックリスト

- [ ] 関数従属性はsample上の偶然ではなく、業務規則か？
- [ ] primary key以外のすべての候補キーを見つけたか？
- [ ] surrogate keyが自然キーの重複を隠していないか？
- [ ] 1NFのatomicityを、用途とdomainを基準に判断したか？
- [ ] 複合キーのpartial dependencyを検査したか？
- [ ] non-keyを介するtransitive dependencyを検査したか？
- [ ] 3NFのprime-attribute例外を正確に適用したか？
- [ ] BCNF分解がdependency preservationを失うか確認したか？
- [ ] 分解がlossless joinであることを検証したか？
- [ ] PK・UNIQUE・FK・CHECKで規則を実際に強制したか？
- [ ] current factとhistorical snapshotを区別したか？
- [ ] 非正規化した値のsourceとrefreshポリシーがあるか？
- [ ] performanceの判断を実際のquery planで確認したか？

## 13. よくある落とし穴

### すべてのtableにIDを一つ付ければ2NFになるという誤解

surrogate primary keyが単一columnだからといって、元の業務上の候補キーにあるpartial dependencyが消えるわけではない。anomalyはそのまま残る。

### NULLが関数従属性を単純にするという誤解

SQLのNULLとthree-valued logic、UNIQUEにおけるNULLの扱いは、DBMSごとの意味を確認しなければならない。必須の業務識別子をnullableにすると、候補キーの論理が曖昧になる。

### 無条件にjoinを減らそうとする設計

joinは関係データベースの基本演算である。重複更新のコストと整合性リスクを無視し、一つのread queryだけを見て統合すると、システム全体のコストが増える可能性がある。

### 正規化ですべての完全性が解決するという誤解

正規形は関数従属性と重複を扱う。範囲constraint、cross-row aggregate、時間の重なり、状態遷移などの規則には、追加のconstraintとtransaction設計が必要である。

### BCNFを機械的に最優先する

dependency preservationを失い、joinや複雑なtriggerなしでは規則を検査できなくなる場合がある。3NFにとどめる方が運用上安全な場合もある。

## まとめ

1NF、2NF、3NF、BCNFは暗記する順序ではなく、異なる重複原因を除去するための判定体系である。

- 1NF：一つのattribute位置に、関係モデル上の一つの値
- 2NF：複合候補キーの一部だけに依存するnon-primeな事実を除去
- 3NF：keyでないattributeを介する間接的な従属性を制御
- BCNF：すべての決定項をsuperkeyに制限

実践での目標は、最も高い数字ではない。**業務規則をDBが一貫して強制し、分解が無損失であり、必要な従属性を運用可能な方法で保存するschema**が目標である。
