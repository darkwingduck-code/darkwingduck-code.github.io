---
title: "Releasing Reproducible Research Software: Releases, CITATION.cff, and Zenodo DOIs"
date: 2026-07-21 10:00:00 +0900
categories: [Research Engineering, Reproducibility]
tags: [research-software, reproducibility, release, git-tag, citation-cff, zenodo, software-doi, preprint]
description: "A procedure for turning a research code repository into a reproducible release and connecting CITATION.cff, a preservation archive, and a software DOI while keeping paper and preprint identifiers separate."
lang: en
hidden: true
translation_key: reproducible-research-software-release-doi
---

{% include language-switcher.html %}

The mere fact that research code is in a public repository does not make it reproducible or citable. The default branch keeps changing, dependencies disappear, and readers have difficulty knowing which commit produced the results.

To publish research software properly, distinguish four objects.

1. The **source repository**, where development continues
2. A **versioned release and tag** that freeze a meaningful state
3. An **archival software record and DOI** for long-term preservation and citation
4. A **paper or preprint** that explains the research question, methods, and results

This article presents a practical procedure for linking these four objects traceably without conflating them.

## 1. First separate what each identifier identifies

| Object | Primary role | Mutability | Typical identifier |
|---|---|---|---|
| repository | collaboration and ongoing development | branches keep changing | repository URL |
| commit | source snapshot | content-addressed and effectively fixed | commit hash |
| tag | human-readable version label | should be immutable by policy | tag name + target commit |
| release | distribution notes and artifact bundle | release notes may be editable | version + release URL |
| software archive | long-term preserved research object | files in a version record are fixed | software DOI |
| preprint/article | research claims and exposition | version policy varies by platform | publication DOI or identifier |
| dataset | input or output data object | should be fixed per version | dataset DOI |

A commit hash points to exact source but does not provide scholarly metadata or a long-term preservation policy. A DOI provides persistent identification and metadata links but does not automatically restore the execution environment. Use both together.

## 2. State the level of reproducibility

Do not merely say “reproducible”; define the supported scope.

- **Source reproducibility**: the same source tree can be obtained.
- **Build reproducibility**: the same executable or package can be built in the specified environment.
- **Computational reproducibility**: the same output can be obtained from the inputs within an allowed tolerance.
- **Result reproducibility**: the figures, tables, and metrics in the paper can be regenerated.
- **Auditability**: code, configuration, and data provenance can be traced backward from a result.

Guaranteeing bitwise-identical output on every platform may be difficult. In that case, specify the supported OS and architecture, numerical tolerance, and nondeterministic components.

## 3. A release is a contract specifying which commit to cite

### The difference among a tag, release, and archive

- A Git tag is a name attached to a specific commit.
- A hosting service release is a distribution object that connects release notes and binary artifacts to a tag.
- An archive is a separate research record that preserves source and metadata for the long term.

The versions of all three objects must match.

~~~text
package metadata version
  = documentation version
  = CITATION.cff version
  = release title
  = git tag
  = archived record version
~~~

### Versioning policy

You can use Semantic Versioning, but first define what constitutes the “public API” of the research software.

- command-line options and file formats
- Python/C++ API
- configuration schema
- semantics of the numerical method or defaults
- output schema and units
- trained weights or parameter bundles

If changing a numerical method or default alters the scientific interpretation of the same input, carefully consider whether it should be treated as a mere patch. The compatibility contract takes precedence over the version number.

### Do not move tags

Force-updating a published tag to a different commit makes the same version name refer to different source. If a correction is needed, create a new patch release and document the known issue in the previous version.

## 4. The reproducibility bundle to include in a release

At minimum, a release needs the following.

### Understanding and execution

- README: purpose, scope, and quick start
- LICENSE: terms for using the source and bundled assets
- environment/lock file
- configuration examples and schema
- input/output data dictionary
- minimal end-to-end example
- known limitations

### Evidence of quality

- automated test results
- analytic or benchmark verification
- numerical tolerance
- deterministic/nondeterministic contract
- supported platform matrix
- changelog and migration notes

### Provenance

- source revision
- release date and version
- dependency lock digest
- container image digest, recorded with the tag if one exists
- input data version or checksum
- commands for generating figures and tables

Do not indiscriminately include large generated outputs and secrets in a source archive. Provide recipes and checksums for reproducible outputs, and link necessary data as a separate archival object after checking its license and privacy constraints.

## 5. The role of CITATION.cff

`CITATION.cff` is a YAML-based citation metadata file that people can read and tools can interpret. Placing it at the repository root lets supported hosting UIs display citation information. The current official CFF guidance and GitHub documentation use the `cff-version: 1.2.0` format in their examples.

The following generic template illustrates its structure.

~~~yaml
cff-version: 1.2.0
message: "If you use this software, please cite this version."
title: "Example Scientific Software"
type: software
version: 1.0.0
date-released: 2026-07-21
license: MIT
repository-code: "https://example.org/example-software"
authors:
  - family-names: "Replace-With-Family-Name"
    given-names: "Replace-With-Given-Name"
~~~

Replace placeholders with actual public metadata and validate the file with a CFF validator. Personal email is not required for a citation; omit it unless there is a reason to publish it.

### Fields that must match at minimum

- software title
- creators and their order
- version
- release date
- repository URL
- license
- version-specific software DOI

Do not determine contributor order automatically from commit counts. Establish authorship eligibility and contributor role policies in advance, and provide separate contributor metadata if necessary.

### How to connect the software itself and a paper

You can present a related paper through `preferred-citation`, but this may cause the repository's citation UI to prioritize citing the paper instead of the software. When credit for the software itself and exact-version reproducibility matter, it is clearer to keep the root citation as the software record and link the paper through references or related identifiers.

## 6. Understand the archive before assigning a DOI

A DOI is not a decorative number in source code but a persistent identifier for a specific research object. According to Zenodo's current guidance, publishing a record registers a DOI, while a new version with changed files is managed as a separate record and persistent identifier.

### Version DOI and Concept DOI

Zenodo DOI versioning provides two categories of DOI upon the first publication.

- **Version DOI**: identifies the files of a specific release
- **Concept DOI**: identifies the collection of all versions and links to the latest version's landing page

The Version DOI is the default when citing the exact code used for reproducibility. The Concept DOI may be appropriate when referring to the evolving software project as a whole.

Do not create versions by arbitrarily appending a suffix such as `.v2` to a DOI string. The archive metadata connects version relationships.

## 7. A safe procedure for connecting Zenodo and a release

The usual flow when using Git hosting integration is as follows.

1. Confirm that the repository can be made public.
2. Run a secret scan, history audit, and license audit.
3. Enable the repository in the archive integration.
4. Freeze the release candidate commit.
5. Run tests, the documentation build, and example reproduction.
6. Align version metadata with `CITATION.cff`.
7. Create an immutable tag and release.
8. Review the archive record's title, creators, resource type, version, and license.
9. After publishing, record the Version DOI and Concept DOI separately.
10. Add the correct relationships to the release page, README, CFF, and paper metadata.

GitHub's official guidance explains that Zenodo integration can issue a DOI for a repository archive and that the integrated repository must be public. Organization repositories may require separate approval for integration access.

### If you want to put the DOI in files before the release

There are two approaches.

- Reserve a DOI in the archive in advance, then add it to the release metadata.
- Archive the first release, add the DOI to the default branch, and fully synchronize version metadata from the next release onward.

Deleting a draft with a reserved DOI may cause you to lose the reservation, so check the archive's current policy. If the same object already has a DOI, do not issue a duplicate DOI; enter the existing DOI in the metadata.

## 8. A Software DOI and a preprint DOI never identify the same object

Software and a preprint are distinct research outputs.

| Distinction | Software record | Preprint record |
|---|---|---|
| Content | source, package, executable, documentation | research question, methods, results, interpretation |
| Resource type | software | preprint/publication |
| Meaning of version | code release | manuscript revision |
| Primary citation target | exact software version that was executed | document version that was read and discussed |
| Identifier | software DOI | preprint DOI/identifier |

Therefore, avoid the following.

- placing a preprint DOI in the software DOI field of `CITATION.cff`
- mixing a preprint file into a software archive and collapsing both into one resource type
- reusing a journal article DOI as the DOI for a supplemental code upload
- forcing code release versions and manuscript revisions into the same numbering scheme

Instead, connect the relationships in archive metadata.

- software **IsSupplementTo** paper
- software **IsDocumentedBy** paper or a separate documentation record
- paper **References** software
- software **Requires** input dataset; dataset **IsRequiredBy** software

Check the actual relation type names in the archive's metadata vocabulary and verify their direction. It is better to provide machine-readable related identifiers than to use prose descriptions alone.

## 9. Freeze source, environment, and data together

Even with a Software DOI, results cannot be reproduced without dependencies and inputs.

### Source

- exact tag and commit
- submodule revisions
- generator version for generated source
- build scripts

### Environment

- dependency lock file
- compiler/interpreter version
- OS and architecture
- numerical libraries and accelerator runtime
- container digest or environment export

Recording only the container tag `latest` may point to a different image over time. Record an immutable digest as well.

### Data and configuration

- input dataset version/DOI
- file checksum
- preprocessing code and order
- configuration file
- random seed and split manifest
- schema and units

If raw data cannot be published, provide a synthetic or minimal example, schema, generator, and access conditions, and state which private components limit full reproduction.

## 10. Automatable release gates

A CI release workflow can check at least the following.

~~~text
[quality]
unit + integration + numerical tests pass
example workflow reproduces expected metrics
documentation builds without broken internal links

[metadata]
package version == tag version
CITATION.cff parses and validates
release date and changelog entry exist
license and notices are present

[security]
secret scan passes
private paths and hostnames are absent
large or restricted data are not bundled

[archive readiness]
source archive is self-contained
dependency lock exists
input/output schema is documented
~~~

Issuing a DOI is itself a publication that changes external state, so using a dry run and human review is safer. A published archival record must not be treated like an ordinary branch.

## 11. Release runbook

### Preparation

- Classify scope and compatibility changes.
- Decide the version.
- Write the changelog and migration notes.
- Review outdated dependencies and licenses.
- Review citation author and contributor metadata.

### Verification

- Build in a clean environment.
- Rerun the minimal example from the beginning.
- Check the commands that generate key figures and tables.
- Check numerical tolerances and platform differences.
- Extract and run the exact source bundle to be archived.

### Publication

- Merge the release commit.
- Apply an annotated/signed tag policy if one exists.
- Publish release notes and artifact checksums.
- Perform a final review of archival record metadata, then publish it.
- Connect the Version DOI to the release and CFF.

### After publication

- Confirm that the DOI resolves to the correct landing page.
- Check the archive's file list and checksums.
- Confirm that Concept and Version DOIs appear as intended.
- Update related identifiers in the repository, documentation, and preprint.
- Create a runbook issue for the next release.

## 12. Verification checklist

- [ ] Have the roles of repository, commit, tag, release, and archive been distinguished?
- [ ] Do tag, package, documentation, CFF, and archive versions match?
- [ ] Is there a policy forbidding movement of published tags?
- [ ] Does the end-to-end example run in a clean environment?
- [ ] Are dependency and input data versions fixed?
- [ ] Is `CITATION.cff` at the root, and does it pass a validator?
- [ ] Do software title, creator order, version, and license match the archive metadata?
- [ ] Are the uses of the Version DOI and Concept DOI distinguished?
- [ ] Are Software DOIs managed separately from preprint/article DOIs?
- [ ] Are related DOIs connected through machine-readable relationships?
- [ ] Are source and archives free of secrets, personal paths, and private data?
- [ ] Is an immutable digest recorded in addition to the container tag?
- [ ] Does a person review the metadata and file bundle before DOI publication?

## 13. Common pitfalls and limitations

### “It is in Git, so it is preserved permanently”

A hosting URL and account are not preservation identifiers. An archive and DOI improve long-term accessibility, but without a license, metadata, and an execution recipe, their usefulness is limited.

### “It has a DOI, so it is reproducible”

A DOI identifies an object. It does not automatically provide dependencies, data, configuration, or numerical tolerances.

### Citing only the latest Concept DOI

A reader may receive a later incompatible version. Reproducing a specific research result requires the Version DOI and release version.

### Copying a DOI manually into the README and causing inconsistencies

Generate CFF, package metadata, release notes, and archive metadata from a single source where possible, or cross-check them in CI.

### Assuming that deleting a record from a public repository also removes its secrets

Secrets may remain in history, forks, CI logs, release artifacts, and archives. After exposure, do not merely delete them; revoke and rotate them immediately and inspect every preservation location.

### Source without an execution contract

Without documentation of supported platforms, tolerances, nondeterministic components, and expected runtime range, it is difficult to determine whether a failure to reproduce is a bug or an environmental difference.

## 14. Official references

- [Official Citation File Format guidance](https://citation-file-format.github.io/)
- [GitHub guidance on citation files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- [Official guidance on preserving a GitHub repository with a DOI](https://docs.github.com/repositories/archiving-a-github-repository/referencing-and-citing-content)
- [Lifecycle of Zenodo records and versions](https://help.zenodo.org/docs/deposit/about-records/)
- [Zenodo DOI versioning guidance](https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning)
- [Zenodo DOI reservation guidance](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)
- [DataCite related identifier relation definitions](https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/)

## Conclusion

The core links for reproducible research software are as follows.

~~~text
result
  -> input/data version
  -> configuration
  -> software version DOI
  -> release tag
  -> exact commit
  -> locked environment
~~~

A paper or preprint is a separate object that explains and makes claims about these links. Separate the DOIs for software and documents, then connect them with related identifiers to preserve both credit and reproducibility.

A good release is not merely “the day the code was published.” It is the state in which a third party no longer has to guess which version to obtain, which environment to use, or what to run.
