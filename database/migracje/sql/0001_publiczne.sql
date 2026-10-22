-- Funkcje publiczne są własnością roli migracyjnej i mają stały search_path.
-- Tylko backend publiczny może je wykonywać; brak ogólnych praw do tabel.
CREATE OR REPLACE FUNCTION public.przygotuj_karte(p_token text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE v_id varchar(36); v_dane jsonb;
BEGIN
  SELECT p.id INTO v_id FROM public.przyrzady p
    JOIN public.linki_qr l ON l.przyrzad_id=p.id
    WHERE l.token=p_token AND l.uniewazniono_at IS NULL AND p.usunieto_at IS NULL
    FOR SHARE OF p,l;
  IF v_id IS NULL THEN RETURN NULL; END IF;
  SELECT jsonb_build_object(
    'numer',p.numer,'typ',t.nazwa,'stan',p.stan,'status',p.status,'wydzial',w.nazwa,
    'klasa',p.klasa,'stan_techniczny',p.stan_techniczny,'komentarz_dat',p.komentarz_dat,
    'wersja',p.wersja,'ostatni',h.ostatni,'interwal',coalesce(h.interwal,12),
    'jednostka',coalesce(h.jednostka,'miesiac'),'nadpisanie',h.nadpisanie,'wynik',h.wynik,
    'proces',CASE WHEN p.klasa='A' THEN 'wzorcowanie' WHEN p.klasa='B' THEN 'sprawdzenie' ELSE NULL END
  ) INTO v_dane FROM public.przyrzady p
    JOIN public.typy_przyrzadow t ON p.typ_id=t.id
    JOIN public.przydzialy a ON a.przyrzad_id=p.id AND a.do_at IS NULL
    JOIN public.wydzialy w ON a.wydzial_id=w.id
    LEFT JOIN public.harmonogramy h ON h.przyrzad_id=p.id
      AND h.proces=CASE WHEN p.klasa='A' THEN 'wzorcowanie' ELSE 'sprawdzenie' END
    WHERE p.id=v_id;
  RETURN v_dane;
END $$;

-- Utrwala migawkę obliczoną przez backend w tej samej transakcji co przygotuj_karte.
-- Deduplikacja identyfikatora obejmuje całą bazę. Nie akceptuje dodatkowych pól JSON.
CREATE OR REPLACE FUNCTION public.zapisz_odczyt(p_token text,p_id text,p_migawka jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE v_link public.linki_qr%ROWTYPE; v_stare public.odczyty_qr%ROWTYPE;
        v_dane jsonb; v_czas timestamptz := clock_timestamp();
BEGIN
  SELECT l.* INTO v_link FROM public.linki_qr l JOIN public.przyrzady p ON p.id=l.przyrzad_id
    WHERE l.token=p_token AND l.uniewazniono_at IS NULL AND p.usunieto_at IS NULL
    FOR SHARE OF p,l;
  IF v_link.id IS NULL THEN RETURN NULL; END IF;
  IF p_id !~ '^[0-9a-f-]{36}$' THEN RETURN NULL; END IF;
  SELECT coalesce(jsonb_object_agg(k,v),'{}'::jsonb) INTO v_dane FROM jsonb_each(p_migawka) x(k,v)
    WHERE k=ANY(ARRAY['numer','typ','stan','status','wydzial','klasa','stan_techniczny',
      'komentarz_dat','wersja','ostatni','interwal','jednostka','nastepny','wynik','proces',
      'metrologiczny','dopuszczenie']);
  INSERT INTO public.odczyty_qr(id,przyrzad_id,link_id,czas,zrodlo,wynik,migawka)
    VALUES(p_id,v_link.przyrzad_id,v_link.id,v_czas,'QR','Sukces',v_dane)
    ON CONFLICT(id) DO NOTHING;
  SELECT * INTO v_stare FROM public.odczyty_qr WHERE id=p_id;
  IF v_stare.link_id<>v_link.id THEN RETURN NULL; END IF;
  RETURN jsonb_build_object('zdarzenie',v_stare.id,'czas',v_stare.czas,'przyrzad',v_stare.migawka);
END $$;

-- Zwraca paginowaną historię statusów bez dostępu do dowolnych migawek i bez zapisu odczytu.
CREATE OR REPLACE FUNCTION public.historia_karty(p_token text,p_strona integer) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
DECLARE v_id varchar(36); v_wpisy jsonb; v_liczba integer;
BEGIN
  SELECT p.id INTO v_id FROM public.przyrzady p JOIN public.linki_qr l ON l.przyrzad_id=p.id
    WHERE l.token=p_token AND l.uniewazniono_at IS NULL AND p.usunieto_at IS NULL;
  IF v_id IS NULL THEN RETURN NULL; END IF;
  SELECT coalesce(jsonb_agg(jsonb_build_object('czas',x.czas,'status',x.migawka->>'metrologiczny',
    'dopuszczenie',x.migawka->'dopuszczenie') ORDER BY x.czas DESC,x.id DESC),'[]'::jsonb),count(*)
    INTO v_wpisy,v_liczba FROM (
      SELECT id,czas,migawka FROM public.odczyty_qr WHERE przyrzad_id=v_id
        ORDER BY czas DESC,id DESC OFFSET (greatest(1,least(p_strona,100000))-1)*20 LIMIT 21
    ) x;
  RETURN jsonb_build_object('wpisy',CASE WHEN v_liczba>20 THEN v_wpisy-20 ELSE v_wpisy END,'dalej',v_liczba>20);
END $$;
REVOKE ALL ON FUNCTION public.przygotuj_karte(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.zapisz_odczyt(text,text,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.historia_karty(text,integer) FROM PUBLIC;
