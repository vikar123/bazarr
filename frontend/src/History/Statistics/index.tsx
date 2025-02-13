import { merge } from "lodash";
import React, {
  FunctionComponent,
  useCallback,
  useEffect,
  useState,
} from "react";
import { Col, Container } from "react-bootstrap";
import { Helmet } from "react-helmet";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDidMount } from "rooks";
import {
  HistoryApi,
  ProvidersApi,
  SystemApi,
  useAsyncRequest,
} from "../../apis";
import {
  AsyncOverlay,
  AsyncSelector,
  ContentHeader,
  LanguageSelector,
  Selector,
} from "../../components";
import { actionOptions, timeframeOptions } from "./options";

function converter(item: History.Stat) {
  const movies = item.movies.map((v) => ({
    date: v.date,
    movies: v.count,
  }));
  const series = item.series.map((v) => ({
    date: v.date,
    series: v.count,
  }));
  const result = merge(movies, series);
  return result;
}

const providerLabel = (item: System.Provider) => item.name;

const SelectorContainer: FunctionComponent = ({ children }) => (
  <Col xs={6} lg={3} className="p-1">
    {children}
  </Col>
);

const HistoryStats: FunctionComponent = () => {
  const [languages, updateLanguages] = useAsyncRequest(
    SystemApi.languages.bind(SystemApi)
  );
  const [providerList, updateProviderParam] = useAsyncRequest(
    ProvidersApi.providers.bind(ProvidersApi)
  );

  const updateProvider = useCallback(
    () => updateProviderParam(true),
    [updateProviderParam]
  );

  useDidMount(() => {
    updateLanguages(true);
  });

  const [timeframe, setTimeframe] = useState<History.TimeframeOptions>("month");
  const [action, setAction] = useState<Nullable<History.ActionOptions>>(null);
  const [lang, setLanguage] = useState<Nullable<Language.Info>>(null);
  const [provider, setProvider] = useState<Nullable<System.Provider>>(null);

  const [stats, update] = useAsyncRequest(HistoryApi.stats.bind(HistoryApi));

  useEffect(() => {
    update(timeframe, action ?? undefined, provider?.name, lang?.code2);
  }, [timeframe, action, provider?.name, lang?.code2, update]);

  return (
    // TODO: Responsive
    <Container fluid className="vh-75">
      <Helmet>
        <title>History Statistics - Bazarr</title>
      </Helmet>
      <AsyncOverlay ctx={stats}>
        {({ content }) => (
          <React.Fragment>
            <ContentHeader scroll={false}>
              <SelectorContainer>
                <Selector
                  placeholder="Time..."
                  options={timeframeOptions}
                  value={timeframe}
                  onChange={(v) => setTimeframe(v ?? "month")}
                ></Selector>
              </SelectorContainer>
              <SelectorContainer>
                <Selector
                  placeholder="Action..."
                  clearable
                  options={actionOptions}
                  value={action}
                  onChange={setAction}
                ></Selector>
              </SelectorContainer>
              <SelectorContainer>
                <AsyncSelector
                  placeholder="Provider..."
                  clearable
                  state={providerList}
                  label={providerLabel}
                  update={updateProvider}
                  onChange={setProvider}
                ></AsyncSelector>
              </SelectorContainer>
              <SelectorContainer>
                <LanguageSelector
                  clearable
                  options={languages.content ?? []}
                  value={lang}
                  onChange={setLanguage}
                ></LanguageSelector>
              </SelectorContainer>
            </ContentHeader>
            <ResponsiveContainer height="100%">
              <BarChart data={content ? converter(content) : []}>
                <CartesianGrid strokeDasharray="4 2"></CartesianGrid>
                <XAxis dataKey="date"></XAxis>
                <YAxis allowDecimals={false}></YAxis>
                <Tooltip></Tooltip>
                <Legend verticalAlign="top"></Legend>
                <Bar name="Series" dataKey="series" fill="#2493B6"></Bar>
                <Bar name="Movies" dataKey="movies" fill="#FFC22F"></Bar>
              </BarChart>
            </ResponsiveContainer>
          </React.Fragment>
        )}
      </AsyncOverlay>
    </Container>
  );
};

export default HistoryStats;
