// Copyright 2020 The SQLFlow Authors. All rights reserved.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package sqlfs

import (
	"database/sql"
	"encoding/base64"
	"fmt"
	"io"

	"sqlflow.org/sqlflow/go/database"
)

func flushToSQLTable(db *sql.DB, table string) func([]byte) error {
	row := 0
	return func(buf []byte) error {
		if db == nil {
			return fmt.Errorf("flushToSQLTable: no database connection")
		}

		if len(buf) > 0 {
			block := base64.StdEncoding.EncodeToString(buf)
			query := fmt.Sprintf("INSERT INTO %s (id, block) VALUES(%d, '%s')",
				table, row, block)
			if _, e := db.Exec(query); e != nil {
				return fmt.Errorf("can't flush to table %s: %v", table, e)
			}
			row++
		}
		return nil
	}
}

func clickhouseFlushToSQLTable(db *sql.DB, table string) func([]byte) error {
	row := 0
	return func(buf []byte) error {
		if db == nil {
			return fmt.Errorf("clickhouse flushToSQLTable: no database connection")
		}
		tx, _ := db.Begin()
		stmt, _ := tx.Prepare(fmt.Sprintf("INSERT INTO %s (id, block) VALUES(?,?)",
			table))

		defer stmt.Close()

		if len(buf) > 0 {
			block := base64.StdEncoding.EncodeToString(buf)

			if _, e := stmt.Exec(row, block); e != nil {
				return fmt.Errorf("clickhouse can't flush to table %s: %v", table, e)
			}
			row++
		}
		if err := tx.Commit(); err != nil {
			return fmt.Errorf("clickhouse can't flush to table %s: %v", table, err)
		}
		return nil
	}
}

func noopWrapUp() error {
	return nil
}

func newSQLWriter(db *database.DB, table string, bufSize int) (io.WriteCloser, error) {
	if e := dropTableIfExists(db.DB, table); e != nil {
		return nil, fmt.Errorf("can't drop table %s: %v", table, e)
	}
	if e := createTable(db, table); e != nil {
		return nil, fmt.Errorf("can't create table %s: %v", table, e)
	}
	if db.DriverName == "clickhouse" {
		return newFlushWriteCloser(clickhouseFlushToSQLTable(db.DB, table), noopWrapUp, bufSize), nil
	}
	return newFlushWriteCloser(flushToSQLTable(db.DB, table), noopWrapUp, bufSize), nil
}
