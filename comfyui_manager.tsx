import { LikeOutlined } from '@ant-design/icons';
import {
  Button,
  Descriptions,
  DescriptionsProps,
  Divider,
  Flex,
  Input,
  List,
  Popconfirm,
  Popover,
} from 'antd';
import { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { NodeProps } from 'reactflow';
import 'reactflow/dist/style.css';
import { NodeDefaultCard } from '../../frontend/components/NodeDefaultCard';
import { HTTP_URL } from '../../frontend/const';
import { GraphContext } from '../../frontend/hooks/graphs';
import { NotificationContext } from '../../frontend/hooks/notification';
import { KatzukiPlugin } from '../../frontend/hooks/types';
import { fetchWithCredentials } from '../../frontend/requests';

// function isSearchWordInTarget(
//   searchWord: string,
//   searchTarget: string,
// ): boolean {
//   const lowerCaseWord = searchWord.toLowerCase();
//   const lowerCaseTarget = searchTarget.toLowerCase();
//   let targetIndex = 0;
//   for (let i = 0; i < lowerCaseWord.length; i++) {
//     const char = lowerCaseWord[i];
//     targetIndex = lowerCaseTarget.indexOf(char, targetIndex);
//     if (targetIndex === -1) {
//       return false;
//     }
//     targetIndex++;
//   }
//   return true;
// }

function isSearchWordInExactTarget(
  searchWord: string,
  searchTarget: string,
): boolean {
  return searchTarget.toLowerCase().includes(searchWord.toLowerCase());
}

export type ComfyUIPlugin = KatzukiPlugin & {
  // author = author
  // title = name
  // reference = url
  files: string[];
  install_type: 'git-clone' | 'copy' | 'unzip';
  // description = description
};

export type ComfyUIRemotePlugin = {
  author;
  title;
  reference;
  files;
  install_type;
  description;
};

export function convertRemoteComfyUIPluginToKatzukiPlugin({
  author,
  title,
  reference,
  files,
  install_type,
  description,
}: ComfyUIRemotePlugin): ComfyUIPlugin {
  return {
    name: title,
    author,
    is_single_file: install_type === 'copy',
    path: undefined,
    url: reference,
    branch: undefined,
    current_commit: undefined,
    upstream_commit: undefined,
    stargazers_count: undefined,
    updated_at: undefined,
    description,
    node_types: undefined,
    commits_hash: undefined,
    commits_message: undefined,
    files,
    install_type,
  };
}

export function ComfyUIManager(node: NodeProps) {
  // Begin KatUI Rows
  const { notificationAPI } = useContext(NotificationContext);

  // Begin Plugin Rows
  const { graph } = useContext(GraphContext);
  const [search, setSearch] = useState<string>('');
  const [installingOrRemoving, setInstallingOrRemoving] = useState(false);
  const [updating, setUpdating] = useState(false);

  const [pluginInfo, setPluginInfo] = useState<{
    [key: string]: ComfyUIPlugin;
  }>({});
  const [installedPluginInfo, setInstalledPluginInfo] = useState<{
    [key: string]: ComfyUIPlugin;
  }>({});

  const fetchPluginInfo = useCallback(() => {
    fetchWithCredentials({
      url: 'https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json',
      notificationAPI: notificationAPI,
      onSuccess: (response) => {
        response
          .json()
          .then((data: { custom_nodes: ComfyUIRemotePlugin[] }) => {
            const pluginInfo: { [key: string]: ComfyUIPlugin } = {};
            data.custom_nodes.forEach((plugin) => {
              pluginInfo[plugin.title] =
                convertRemoteComfyUIPluginToKatzukiPlugin(plugin);
            });
            setPluginInfo(pluginInfo);
          });
      },
      onFailed: () => {},
      withoutCredentials: true,
    });
  }, [notificationAPI]);

  const fetchInstalledPluginInfo = useCallback(() => {
    fetchWithCredentials({
      url: `${HTTP_URL}/ComfyUIManager/plugins`,
      notificationAPI: notificationAPI,
      onSuccess: (response) => {
        response.json().then((pluginInfo: { [key: string]: ComfyUIPlugin }) => {
          setInstalledPluginInfo(pluginInfo);
        });
      },
      onFailed: () => {},
      withoutCredentials: true,
    });
  }, [notificationAPI]);

  useEffect(() => {
    fetchPluginInfo();
    fetchInstalledPluginInfo();
  }, [fetchPluginInfo, fetchInstalledPluginInfo]);

  const onRemove = useCallback(
    (plugin: ComfyUIPlugin) => {
      setInstallingOrRemoving(true);
      fetchWithCredentials({
        url: `${HTTP_URL}/ComfyUIManager/plugins/remove`,
        notificationAPI: notificationAPI,
        onSuccess: (response) => {
          setInstallingOrRemoving(false);
          notificationAPI.success({
            message: 'Plugin Removed',
            description: `Plugin ${plugin.name} has been removed. Please restart the program for it to take effect.`,
          });
          fetchPluginInfo();
        },
        onFailed: () => {
          setInstallingOrRemoving(false);
        },
        options: {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(plugin),
        },
      });
    },
    [notificationAPI, fetchPluginInfo],
  );
  const onInstall = useCallback(
    (plugin: ComfyUIPlugin) => {
      setInstallingOrRemoving(true);
      fetchWithCredentials({
        url: `${HTTP_URL}/ComfyUIManager/plugins/install`,
        notificationAPI: notificationAPI,
        onSuccess: (response) => {
          setInstallingOrRemoving(false);
          notificationAPI.success({
            message: 'Plugin Installed',
            description: `Plugin from ${plugin.name} has been installed. Please restart the program for it to take effect.`,
          });
          fetchPluginInfo();
        },
        onFailed: () => {
          setInstallingOrRemoving(false);
        },
        options: {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(plugin),
        },
      });
    },
    [notificationAPI, fetchPluginInfo],
  );

  const pluginInfoToList = useCallback(
    (pluginInfo: { [key: string]: ComfyUIPlugin }) => {
      return (
        <List
          size="small"
          split={false}
          pagination={{ position: 'bottom', align: 'center' }}
          dataSource={Object.values(pluginInfo).sort((a, b) =>
            a.name.localeCompare(b.name),
          )}
          renderItem={(item, index) => {
            const dataSource = item.commits_hash
              ? item.commits_hash.map((key, index) => {
                  return {
                    hash: key.substring(0, 7),
                    message: item.commits_message
                      ? item.commits_message[index]
                      : '',
                  };
                })
              : [];
            const revertList =
              dataSource.length === 0 ? (
                <></>
              ) : (
                <List
                  size="small"
                  split={false}
                  pagination={{ position: 'bottom', align: 'center' }}
                  dataSource={dataSource}
                  renderItem={(commitItem, index) => {
                    return (
                      <List.Item>
                        <Popconfirm
                          title="Revert to this version of the plugin?"
                          description={
                            <>
                              <p>
                                {
                                  'DATA LOSS WARNING: Reverting to a previous version of the plugin might cause loss of data.'
                                }
                              </p>
                              <p>
                                {
                                  "For users: If you didn't change existing code, there will be no data lost."
                                }
                              </p>
                              <p>
                                {
                                  'For plugin dev: This will perform `reset --hard`. Please make sure you are in a clean state before reverting.'
                                }
                              </p>
                            </>
                          }
                          onConfirm={async () => {
                            return fetchWithCredentials({
                              url: `${HTTP_URL}/ComfyUIManager/plugin/${item.name}/revert/${commitItem.hash}`,
                              notificationAPI: notificationAPI,
                              onSuccess: (response) => {
                                notificationAPI.success({
                                  message: 'Reverted',
                                  description: `Reverted to commit ${commitItem.hash}. Please restart the program for it to take effect.`,
                                });
                                fetchPluginInfo();
                              },
                              onFailed: () => {},
                            });
                          }}
                        >
                          <Button size="small" type="text" className="nodrag">
                            <div
                              style={{
                                fontFamily: 'monospace',
                              }}
                            >
                              {commitItem.hash}: {commitItem.message}
                            </div>
                          </Button>
                        </Popconfirm>
                      </List.Item>
                    );
                  }}
                />
              );
            const items: DescriptionsProps['items'] = [
              {
                key: '1',
                label: 'Name',
                children: item.name,
              },
              {
                key: '2',
                label: 'Author',
                children: item.author,
              },
              {
                key: '3',
                label: 'Path',
                children: item.path,
              },
              {
                key: '4',
                label: 'Url',
                children: (
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.url}
                  </a>
                ),
              },
              {
                key: '5',
                label: 'Branch',
                children: item.branch,
              },
              {
                key: '6',
                label: 'Current Commit',
                children: item.current_commit,
              },
              {
                key: '7',
                label: 'Upstream Commit',
                children: item.upstream_commit,
              },
              {
                key: '8',
                label: 'Updated At',
                children: item.updated_at,
              },
              {
                key: '9',
                label: 'Description',
                children: item.description,
              },
              {
                key: '10',
                label: 'Nodes',
                children: item.node_types ? item.node_types.join(', ') : '',
              },
              {
                key: '11',
                label: 'Files',
                children: item.files ? item.files.join(', ') : '',
              },
              {
                key: '12',
                label: 'Install Type',
                children: item.install_type,
              },
              {
                key: '13',
                label: 'Actions',
                children: (
                  <div>
                    <div>
                      <Button
                        size="small"
                        className="nodrag"
                        onClick={() =>
                          item.path ? onRemove(item) : onInstall(item)
                        }
                        loading={installingOrRemoving}
                      >
                        {item.path ? 'Remove' : 'Install'}
                      </Button>

                      <Button
                        size="small"
                        className="nodrag"
                        onClick={() => {
                          // TODO: update plugin is currently not supported
                        }}
                        disabled={
                          !item.path ||
                          item.current_commit === item.upstream_commit
                        }
                        loading={updating}
                      >
                        Update
                      </Button>
                    </div>
                    <Divider />
                    {revertList}
                  </div>
                ),
              },
            ];
            return (
              <List.Item style={{ padding: 0 }}>
                <Popover
                  trigger={'click'}
                  mouseEnterDelay={0.2}
                  mouseLeaveDelay={0.0}
                  placement="top"
                  content={
                    <Descriptions
                      size="small"
                      column={1}
                      items={items}
                      style={{
                        maxWidth: 500,
                        maxHeight: 500,
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                      }}
                    />
                  }
                  title={'Node Info'}
                >
                  <Button
                    size="small"
                    className="nodrag"
                    style={{ width: '100%' }}
                  >
                    <Flex
                      gap="middle"
                      vertical={false}
                      justify="space-between"
                      align="center"
                    >
                      <div>
                        {item.name +
                          ` (${Object.values(graph.nodes)
                            .map((node) => {
                              if (!item.node_types) return 0;
                              return item.node_types.includes(node.type)
                                ? 1
                                : 0;
                            })
                            .reduce((a: number, b: number) => a + b, 0)})`}
                      </div>
                      <div>
                        {item.stargazers_count !== null ? (
                          <>
                            {item.stargazers_count}
                            <LikeOutlined
                              style={{
                                marginLeft: 5,
                              }}
                            />
                          </>
                        ) : (
                          'Local'
                        )}
                      </div>
                    </Flex>
                  </Button>
                </Popover>
              </List.Item>
            );
          }}
        />
      );
    },
    [
      onRemove,
      graph.nodes,
      onInstall,
      installingOrRemoving,
      updating,
      notificationAPI,
      fetchPluginInfo,
    ],
  );

  const pluginRows = useMemo(() => {
    return pluginInfoToList(installedPluginInfo);
  }, [installedPluginInfo, pluginInfoToList]);

  const pluginRowsRemote = useMemo(() => {
    const mergedPluginInfo = { ...pluginInfo, ...installedPluginInfo };

    return pluginInfoToList(
      Object.fromEntries(
        Object.entries(mergedPluginInfo).filter(
          ([key, value]) =>
            !value.path &&
            (search === '' ||
              isSearchWordInExactTarget(search, value.name) ||
              isSearchWordInExactTarget(search, value.author) ||
              (value.description &&
                isSearchWordInExactTarget(search, value.description)) ||
              (value.node_types &&
                isSearchWordInExactTarget(search, value.node_types.join(',')))),
        ),
      ),
    );
  }, [pluginInfo, installedPluginInfo, pluginInfoToList, search]);

  const items = useMemo(
    () => [
      {
        name: 'Installed Plugins',
        children: pluginRows,
      },
      {
        name: 'Plugins Repo',
        children: (
          <>
            <div>
              <Flex
                gap="small"
                vertical={false}
                justify="space-between"
                align="center"
              >
                <Input
                  variant="filled"
                  size="small"
                  className="nodrag"
                  placeholder={'Search'}
                  onChange={(event) => {
                    setSearch(event.target.value);
                  }}
                />
              </Flex>
            </div>
            <div>{pluginRowsRemote}</div>
          </>
        ),
      },
    ],
    [pluginRows, pluginRowsRemote],
  );

  if (!graph.nodes[node.id]) {
    // BUG: this might trigger error: Cannot read properties of undefined (reading 'data') during hot reload and delete. This is due to node.id isn't updated and it tries to keep the original component (node still rendered when it shouldn't).
    console.warn(
      'Node ' + node.id + ' of type ' + node.type + ' is not in graph.nodes',
    );
    return <></>;
  }

  return (
    <NodeDefaultCard
      items={items}
      nodeId={node.id}
      nodeType={node.type}
      nodeDataState={node.data.state}
      nodeDataInput={node.data.input}
      nodeDataCachePolicy={node.data.cachePolicy}
      nodeDataOutput={node.data.output}
    />
  );
}
